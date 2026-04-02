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
