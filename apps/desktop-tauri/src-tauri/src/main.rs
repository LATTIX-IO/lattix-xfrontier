// Lattix xFrontier desktop shell (Tauri v2).
//
// Topology: this shell spawns ONE backend sidecar — the packaged supervisor
// (`frontier-backend`, see frontier_tooling/desktop_main.py) — which in turn
// brings up every native service (Postgres+pgvector, Neo4j world models, NATS,
// Ollama, the confined agents, the FastAPI backend, and the Next.js frontend).
// Once the backend reports healthy, we navigate the webview to the local UI.
//
// We intentionally keep the heavy lifting in Python (the supervisor) so the Rust
// layer stays a thin, auditable window + lifecycle manager.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::time::Duration;

use tauri::{Emitter, Manager, WebviewUrl};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

const BACKEND_HEALTH_URL: &str = "http://127.0.0.1:8000/healthz";
const FRONTEND_URL: &str = "http://127.0.0.1:3000";
const HEALTH_TIMEOUT_SECS: u64 = 180;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            // Spawn the packaged supervisor sidecar. The binary is resolved from
            // the bundle's `externalBin` (name + target triple suffix).
            let sidecar = app
                .shell()
                .sidecar("frontier-backend")
                .expect("frontier-backend sidecar is missing from the bundle");
            let (mut rx, _child) = sidecar
                .spawn()
                .expect("failed to spawn the frontier-backend sidecar");

            // Drain sidecar stdout/stderr; surface first-run progress to the splash.
            let drain_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line).to_string();
                            println!("[backend] {text}");
                            // The supervisor prefixes provisioning lines with
                            // "[firstrun]"; forward them to the loading page.
                            if let Some(msg) = text.split("[firstrun]").nth(1) {
                                let _ = drain_handle.emit("firstrun-progress", msg.trim().to_string());
                            }
                        }
                        CommandEvent::Stderr(line) => {
                            let text = String::from_utf8_lossy(&line).to_string();
                            eprintln!("[backend] {text}");
                            if let Some(msg) = text.split("[firstrun]").nth(1) {
                                let _ = drain_handle.emit("firstrun-progress", msg.trim().to_string());
                            }
                        }
                        CommandEvent::Terminated(payload) => {
                            eprintln!("[backend] terminated: {:?}", payload);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            // Navigate once the frontend port is accepting connections (the UI
            // we load). The in-process backend on :8000 comes up first.
            tauri::async_runtime::spawn(async move {
                let _ = wait_for_health(BACKEND_HEALTH_URL, HEALTH_TIMEOUT_SECS).await;
                if wait_for_health(FRONTEND_URL, HEALTH_TIMEOUT_SECS).await {
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.navigate(FRONTEND_URL.parse().unwrap());
                    }
                } else {
                    eprintln!("frontend did not become reachable within {HEALTH_TIMEOUT_SECS}s");
                }
            });

            // The main window starts on the bundled `loading` page (frontendDist).
            let _ = WebviewUrl::default();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running the Lattix xFrontier desktop shell");
}

/// Poll the backend health endpoint until it responds or the timeout elapses.
async fn wait_for_health(url: &str, timeout_secs: u64) -> bool {
    let deadline = std::time::Instant::now() + Duration::from_secs(timeout_secs);
    let client = match reqwest_like_get() {
        Some(c) => c,
        None => return false,
    };
    while std::time::Instant::now() < deadline {
        if client(url) {
            return true;
        }
        tokio_sleep(Duration::from_millis(750)).await;
    }
    false
}

// The desktop shell avoids an extra HTTP dependency: a tiny std TCP probe is
// enough to know the backend port is accepting connections. Swap for a real
// HTTP client if a status-code check is needed.
fn reqwest_like_get() -> Option<fn(&str) -> bool> {
    Some(|url: &str| {
        // url is http://host:port/path — extract host:port and TCP-probe it.
        let trimmed = url.trim_start_matches("http://");
        let authority = trimmed.split('/').next().unwrap_or("");
        std::net::TcpStream::connect_timeout(
            &match authority.to_socket_addrs_first() {
                Some(addr) => addr,
                None => return false,
            },
            Duration::from_millis(500),
        )
        .is_ok()
    })
}

trait ToSocketAddrsFirst {
    fn to_socket_addrs_first(&self) -> Option<std::net::SocketAddr>;
}

impl ToSocketAddrsFirst for str {
    fn to_socket_addrs_first(&self) -> Option<std::net::SocketAddr> {
        use std::net::ToSocketAddrs;
        self.to_socket_addrs().ok().and_then(|mut it| it.next())
    }
}

async fn tokio_sleep(d: Duration) {
    tauri::async_runtime::spawn_blocking(move || std::thread::sleep(d))
        .await
        .ok();
}
