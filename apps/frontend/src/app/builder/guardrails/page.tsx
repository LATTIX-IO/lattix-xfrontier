import Link from "next/link";
import { TypedDeleteButton } from "@/components/typed-delete-button";
import { getGuardrailRulesets } from "@/lib/api";

export default async function GuardrailsBuilderPage() {
  const rulesets = await getGuardrailRulesets();

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Guardrails Builder</h1>
          <p className="fx-muted">Production-ready preconfigured guardrails plus custom sets for agents and workflows.</p>
        </div>
        <Link href="/builder/guardrails/new" className="fx-btn-primary px-3 py-2 text-sm">
          New guardrail set
        </Link>
      </header>

      <div className="fx-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Version</th>
              <th className="px-3 py-2 text-left">Guardrail ID</th>
              <th className="px-3 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {rulesets.map((ruleset) => (
              <tr key={ruleset.id} className="border-t border-[var(--fx-border)]">
                <td className="px-3 py-2 text-[var(--foreground)]">{ruleset.name}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">{ruleset.status}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">v{ruleset.version}</td>
                <td className="px-3 py-2 font-mono text-xs text-[var(--foreground)]">{ruleset.id}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <Link className="fx-btn-secondary px-3 py-1.5 text-xs font-medium" href={`/builder/guardrails/${ruleset.id}`}>
                      Open
                    </Link>
                    <TypedDeleteButton itemType="guardrail" itemId={ruleset.id} itemName={ruleset.name} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
