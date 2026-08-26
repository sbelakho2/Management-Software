{{/*
Expand the name of the chart.
*/}}
{{- define "sensei.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "sensei.fullname" -}}
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
{{- define "sensei.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "sensei.labels" -}}
helm.sh/chart: {{ include "sensei.chart" . }}
{{ include "sensei.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "sensei.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sensei.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "sensei.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "sensei.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "sensei.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "sensei.fullname" .) }}
{{- else }}
{{- .Values.config.databaseHost }}
{{- end }}
{{- end }}

{{/*
PostgreSQL database URL
*/}}
{{- define "sensei.postgresql.url" -}}
{{- if .Values.config.databaseUrl }}
{{- .Values.config.databaseUrl }}
{{- else }}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "sensei.postgresql.host" .) .Values.postgresql.auth.database }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "sensei.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "sensei.fullname" .) }}
{{- else }}
{{- .Values.config.redisHost }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "sensei.redis.url" -}}
{{- if .Values.config.redisUrl }}
{{- .Values.config.redisUrl }}
{{- else }}
{{- if .Values.redis.auth.enabled }}
{{- printf "redis://:%s@%s:6379/0" .Values.redis.auth.password (include "sensei.redis.host" .) }}
{{- else }}
{{- printf "redis://%s:6379/0" (include "sensei.redis.host" .) }}
{{- end }}
{{- end }}
{{- end }}

{{/*
MinIO endpoint
*/}}
{{- define "sensei.minio.endpoint" -}}
{{- if .Values.minio.enabled }}
{{- printf "http://%s-minio:9000" (include "sensei.fullname" .) }}
{{- else }}
{{- .Values.config.storage.endpoint }}
{{- end }}
{{- end }}

{{/*
NATS URL: includes the auth token when NATS auth is enabled.
*/}}
{{- define "sensei.nats.url" -}}
{{- if .Values.nats.auth.enabled -}}
nats://{{ .Values.nats.auth.user }}:{{ .Values.nats.auth.password }}@{{ .Release.Name }}-nats:4222
{{- else -}}
nats://{{ .Release.Name }}-nats:4222
{{- end -}}
{{- end -}}
