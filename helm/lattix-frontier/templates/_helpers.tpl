{{- define "lattix-frontier.name" -}}
lattix-frontier
{{- end -}}

{{- define "lattix-frontier.fullname" -}}
{{ include "lattix-frontier.name" . }}
{{- end -}}

{{- define "lattix-frontier.labels" -}}
app.kubernetes.io/name: {{ include "lattix-frontier.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "lattix-frontier.name" . }}-{{ .Chart.Version }}
{{- end -}}

{{- define "lattix-frontier.imageRef" -}}
{{- $image := . -}}
{{- if kindIs "string" $image -}}
{{- $image -}}
{{- else -}}
{{- $repository := default "" $image.repository -}}
{{- $tag := default "" $image.tag -}}
{{- $digest := default "" $image.digest -}}
{{- if and $repository $digest -}}
{{- printf "%s@%s" $repository $digest -}}
{{- else if and $repository $tag -}}
{{- printf "%s:%s" $repository $tag -}}
{{- else -}}
{{- $repository -}}
{{- end -}}
{{- end -}}
{{- end -}}
