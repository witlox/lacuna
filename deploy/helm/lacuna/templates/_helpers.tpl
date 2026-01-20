{{/*
Expand the name of the chart.
*/}}
{{- define "lacuna.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "lacuna.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "lacuna.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "lacuna.labels" -}}
helm.sh/chart: {{ include "lacuna.chart" . }}
{{ include "lacuna.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "lacuna.selectorLabels" -}}
app.kubernetes.io/name: {{ include "lacuna.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "lacuna.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "lacuna.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database URL
*/}}
{{- define "lacuna.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
postgresql://{{ .Values.postgresql.auth.username }}:$(DATABASE_PASSWORD)@{{ include "lacuna.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else }}
postgresql://{{ .Values.externalDatabase.username }}:$(DATABASE_PASSWORD)@{{ .Values.externalDatabase.host }}:{{ .Values.externalDatabase.port }}/{{ .Values.externalDatabase.database }}?sslmode={{ .Values.externalDatabase.sslMode }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "lacuna.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- if .Values.redis.auth.enabled }}
redis://:$(REDIS_PASSWORD)@{{ include "lacuna.fullname" . }}-redis-master:6379/0
{{- else }}
redis://{{ include "lacuna.fullname" . }}-redis-master:6379/0
{{- end }}
{{- else }}
{{- if .Values.secrets.redisPassword }}
redis://:$(REDIS_PASSWORD)@{{ .Values.externalRedis.host }}:{{ .Values.externalRedis.port }}/0
{{- else }}
redis://{{ .Values.externalRedis.host }}:{{ .Values.externalRedis.port }}/0
{{- end }}
{{- end }}
{{- end }}

{{/*
OPA endpoint
*/}}
{{- define "lacuna.opaEndpoint" -}}
{{- if .Values.opa.enabled }}
http://{{ include "lacuna.fullname" . }}-opa:8181
{{- else }}
{{ .Values.config.policy.opaEndpoint }}
{{- end }}
{{- end }}
