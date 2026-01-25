/**
 * AI Email Drafting Components
 *
 * Provides UI for AI-powered email draft generation:
 * - EmailComposer: Main email composition interface
 * - EmailDraftPreview: Preview generated draft
 * - RecipientSelector: Select/add recipients
 * - ToneSelector: Choose email tone
 * - PurposeSelector: Choose email purpose
 * - CompliancePanel: View compliance issues
 * - SuggestionsPanel: View improvement suggestions
 */

'use client';

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  useEmailDraftingStore,
  EmailTone,
  EmailPurpose,
  Language,
  DraftStatus,
  Recipient,
  GeneratedDraft,
  GenerationRequest,
  getPurposeLabelKey,
  getToneLabelKey,
  getLanguageLabelKey,
  getStatusLabelKey,
  getStatusColorClass,
  getConfidenceColorClass,
  formatConfidenceScore,
  formatGenerationTime,
  generateId,
  createRecipient,
  validateRecipient,
} from '@/stores/email-drafting-store';
import { useAuthStore } from '@/stores';
import { apiClient } from '@/api/client';
import { ErrorBoundary } from '@/components/error-boundary';
import { useI18n } from '@/contexts/i18n-context';

// ============================================================================
// Icons
// ============================================================================

const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
  </svg>
);

const SparklesIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707" />
    <path d="M12 8l1.5 3L17 12.5 13.5 14 12 17l-1.5-3L7 12.5l3.5-1.5L12 8z" />
  </svg>
);

const RefreshIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M23 4v6h-6M1 20v-6h6" />
    <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
  </svg>
);

const CheckIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

const XIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18 6L6 18M6 6l12 12" />
  </svg>
);

const EditIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

const CopyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
  </svg>
);

const AlertIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4M12 16h.01" />
  </svg>
);

const LightbulbIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 18h6M10 22h4" />
    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14" />
  </svg>
);

const UserIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const MailIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="M22 6l-10 7L2 6" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M6 9l6 6 6-6" />
  </svg>
);

// ============================================================================
// Purpose Selector
// ============================================================================

interface PurposeSelectorProps {
  value: EmailPurpose | null;
  onChange: (purpose: EmailPurpose) => void;
  className?: string;
}

export function PurposeSelector({ value, onChange, className = '' }: PurposeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useI18n();

  const purposes: EmailPurpose[] = [
    'missing_info_request',
    'quote_followup',
    'quote_submission',
    'supplier_inquiry',
    'meeting_request',
    'meeting_confirmation',
    'issue_notification',
    'status_update',
    'thank_you',
    'introduction',
    'custom',
  ];

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between rounded-rams-sm border border-rams-line bg-rams-panel px-4 py-2 text-left hover:border-rams-border focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
        aria-label={t('emailDrafting.aria.selectPurpose')}
        aria-expanded={isOpen}
      >
        <span className={value ? 'text-rams-foreground' : 'text-rams-muted'}>
          {value ? t(getPurposeLabelKey(value)) : t('emailDrafting.placeholders.selectPurpose')}
        </span>
        <ChevronDownIcon />
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-rams-sm border border-rams-line bg-rams-module py-1">
          {purposes.map((purpose) => (
            <button
              key={purpose}
              type="button"
              onClick={() => {
                onChange(purpose);
                setIsOpen(false);
              }}
              className={`block w-full px-4 py-2 text-left hover:bg-rams-panel ${
                value === purpose ? 'bg-rams-panel text-rams-steel' : 'text-rams-foreground'
              }`}
            >
              {t(getPurposeLabelKey(purpose))}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Tone Selector
// ============================================================================

interface ToneSelectorProps {
  value: EmailTone;
  onChange: (tone: EmailTone) => void;
  className?: string;
}

export function ToneSelector({ value, onChange, className = '' }: ToneSelectorProps) {
  const { t } = useI18n();
  const tones: EmailTone[] = [
    'formal',
    'professional',
    'friendly',
    'urgent',
    'apologetic',
    'appreciative',
    'concise',
  ];

  return (
    <div className={`flex flex-wrap gap-2 ${className}`} role="radiogroup" aria-label={t('emailDrafting.aria.toneGroup')}>
      {tones.map((tone) => (
        <button
          key={tone}
          type="button"
          role="radio"
          aria-checked={value === tone}
          onClick={() => onChange(tone)}
          className={`rounded-rams-sm px-3 py-1 text-sm font-medium transition-colors ${
            value === tone
              ? 'bg-rams-steel text-rams-foreground'
              : 'bg-rams-panel text-rams-foreground hover:bg-rams-module'
          }`}
        >
          {t(getToneLabelKey(tone))}
        </button>
      ))}
    </div>
  );
}

// ============================================================================
// Language Selector
// ============================================================================

interface LanguageSelectorProps {
  value: Language;
  onChange: (language: Language) => void;
  className?: string;
}

export function LanguageSelector({ value, onChange, className = '' }: LanguageSelectorProps) {
  const { t } = useI18n();
  const languages: Language[] = ['en', 'fr', 'de', 'es', 'it', 'pt'];

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as Language)}
      className={`rounded-rams-sm border border-rams-line bg-rams-panel px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20 ${className}`}
      aria-label={t('emailDrafting.aria.selectLanguage')}
    >
      {languages.map((lang) => (
        <option key={lang} value={lang}>
          {t(getLanguageLabelKey(lang))}
        </option>
      ))}
    </select>
  );
}

// ============================================================================
// Recipient Input
// ============================================================================

interface RecipientInputProps {
  value: string;
  name: string;
  onEmailChange: (email: string) => void;
  onNameChange: (name: string) => void;
  recentRecipients: { recipient: Recipient; lastUsed: Date }[];
  onSelectRecent: (recipient: Recipient) => void;
  className?: string;
}

export function RecipientInput({
  value,
  name,
  onEmailChange,
  onNameChange,
  recentRecipients,
  onSelectRecent,
  className = '',
}: RecipientInputProps) {
  const { t } = useI18n();
  const [showRecents, setShowRecents] = useState(false);
  const errors = validateRecipient({ email: value });

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="email"
            value={value}
            onChange={(e) => onEmailChange(e.target.value)}
            onFocus={() => setShowRecents(true)}
            onBlur={() => setTimeout(() => setShowRecents(false), 200)}
            placeholder={t('emailDrafting.placeholders.recipientEmail')}
            className={`w-full rounded-rams-sm border px-4 py-2 focus:outline-none focus:ring-2 ${
              errors.length > 0 && value
                ? 'border-rams-red focus:border-rams-red focus:ring-rams-red/20'
                : 'border-rams-line focus:border-rams-steel focus:ring-rams-steel/20'
            }`}
            aria-label={t('emailDrafting.aria.recipientEmail')}
            aria-invalid={errors.length > 0 && value.length > 0}
          />

          {showRecents && recentRecipients.length > 0 && (
            <div className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-rams-sm border border-rams-line bg-rams-module py-1">
              {recentRecipients.slice(0, 5).map(({ recipient }) => (
                <button
                  key={recipient.email}
                  type="button"
                  onClick={() => onSelectRecent(recipient)}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left hover:bg-rams-panel"
                >
                  <UserIcon />
                  <div>
                    <div className="text-sm font-medium text-rams-foreground">
                      {recipient.name || recipient.email}
                    </div>
                    {recipient.name && (
                      <div className="text-xs text-rams-muted">{recipient.email}</div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={t('emailDrafting.placeholders.recipientNameOptional')}
          className="w-40 rounded-rams-sm border border-rams-line px-4 py-2 focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
          aria-label={t('emailDrafting.aria.recipientName')}
        />
      </div>
      {errors.length > 0 && value && (
        <p className="text-sm text-rams-red">{t(errors[0])}</p>
      )}
    </div>
  );
}

// ============================================================================
// Key Points Editor
// ============================================================================

interface KeyPointsEditorProps {
  points: string[];
  onChange: (points: string[]) => void;
  className?: string;
}

export function KeyPointsEditor({ points, onChange, className = '' }: KeyPointsEditorProps) {
  const { t } = useI18n();
  const [newPoint, setNewPoint] = useState('');

  const addPoint = () => {
    if (newPoint.trim()) {
      onChange([...points, newPoint.trim()]);
      setNewPoint('');
    }
  };

  const removePoint = (index: number) => {
    onChange(points.filter((_, i) => i !== index));
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex gap-2">
        <input
          type="text"
          value={newPoint}
          onChange={(e) => setNewPoint(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addPoint())}
          placeholder={t('emailDrafting.placeholders.keyPoint')}
          className="flex-1 rounded-rams-sm border border-rams-line px-4 py-2 focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
          aria-label={t('emailDrafting.aria.addKeyPoint')}
        />
        <button
          type="button"
          onClick={addPoint}
          className="rounded-rams-sm bg-rams-panel px-4 py-2 text-sm font-medium text-rams-foreground hover:bg-rams-module"
        >
          {t('emailDrafting.actions.add')}
        </button>
      </div>
      {points.length > 0 && (
        <ul className="list-disc space-y-1 pl-5" aria-label={t('emailDrafting.aria.keyPointsList')}>
          {points.map((point, index) => (
            <li
              key={index}
              className="relative list-item rounded-rams-sm bg-rams-panel px-3 py-2 text-sm text-rams-foreground"
            >
              <span className="pr-8">{point}</span>
              <button
                type="button"
                onClick={() => removePoint(index)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-rams-muted hover:text-rams-red"
                aria-label={t('emailDrafting.aria.removeKeyPoint', { point, نقطة: point })}
              >
                <XIcon />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ============================================================================
// Draft Preview
// ============================================================================

interface DraftPreviewProps {
  draft: GeneratedDraft;
  onEdit: (field: 'subject' | 'body' | 'salutation' | 'closing') => void;
  onCopy: () => void;
  className?: string;
}

export function DraftPreview({ draft, onEdit, onCopy, className = '' }: DraftPreviewProps) {
  const { t } = useI18n();
  return (
    <div className={`rounded-rams-sm border border-rams-line bg-rams-module ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-rams-line bg-rams-panel px-4 py-3">
        <div className="flex items-center gap-2">
          <MailIcon />
          <span className="font-medium text-rams-foreground">{t('emailDrafting.preview.title')}</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1 rounded-rams-sm border border-rams-line bg-rams-panel px-2 py-1 text-xs font-medium ${getStatusColorClass(
              draft.status
            )}`}
          >
            {t(getStatusLabelKey(draft.status))}
          </div>
          <button
            type="button"
            onClick={onCopy}
            className="rounded-rams-sm p-1 text-rams-muted hover:bg-rams-panel hover:text-rams-foreground"
            aria-label={t('emailDrafting.aria.copyToClipboard')}
          >
            <CopyIcon />
          </button>
        </div>
      </div>

      {/* Subject */}
      <div className="border-b border-rams-line px-4 py-2">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs text-rams-muted">{t('emailDrafting.preview.subjectLabel')}</span>
            <span className="font-medium text-rams-foreground">{draft.subject}</span>
          </div>
          <button
            type="button"
            onClick={() => onEdit('subject')}
            className="rounded-rams-sm p-1 text-rams-muted hover:bg-rams-panel hover:text-rams-foreground"
            aria-label={t('emailDrafting.aria.editSubject')}
          >
            <EditIcon />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-4">
        <div className="whitespace-pre-wrap font-sans text-sm text-rams-foreground">
          {draft.bodyPlain}
        </div>
      </div>

      {/* Footer stats */}
      <div className="flex items-center justify-between border-t border-rams-line px-4 py-2 text-xs text-rams-muted">
        <div className="flex items-center gap-4">
          <span
            className={`flex items-center gap-1 ${getConfidenceColorClass(
              draft.confidenceScore
            )}`}
          >
            {t('emailDrafting.preview.confidence', {
              score: formatConfidenceScore(draft.confidenceScore),
              درجة: formatConfidenceScore(draft.confidenceScore),
            })}
          </span>
          <span>
            {t('emailDrafting.preview.generatedIn', {
              time: formatGenerationTime(draft.generationTimeMs, {
                milliseconds: t('emailDrafting.units.milliseconds'),
                seconds: t('emailDrafting.units.seconds'),
              }),
              زمن: formatGenerationTime(draft.generationTimeMs, {
                milliseconds: t('emailDrafting.units.milliseconds'),
                seconds: t('emailDrafting.units.seconds'),
              }),
            })}
          </span>
        </div>
        <button
          type="button"
          onClick={() => onEdit('body')}
          className="flex items-center gap-1 text-rams-steel hover:opacity-90"
        >
          <EditIcon />
          {t('emailDrafting.actions.edit')}
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Compliance Panel
// ============================================================================

interface CompliancePanelProps {
  issues: string[];
  className?: string;
}

export function CompliancePanel({ issues, className = '' }: CompliancePanelProps) {
  const { t } = useI18n();
  if (issues.length === 0) {
    return (
      <div className={`rounded-rams-sm border border-rams-line bg-rams-panel p-4 ${className}`}>
        <div className="flex items-center gap-2 text-rams-green">
          <CheckIcon />
          <span className="font-medium">{t('emailDrafting.compliance.none')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-rams-sm border border-rams-line bg-rams-panel p-4 ${className}`}>
      <div className="flex items-center gap-2 text-rams-orange">
        <AlertIcon />
        <span className="font-medium">
          {t('emailDrafting.compliance.title', { count: issues.length, عدد: issues.length })}
        </span>
      </div>
      <ul className="mt-2 list-disc space-y-1 pl-5">
        {issues.map((issue, index) => (
          <li key={index} className="text-sm text-rams-orange">
            {issue}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ============================================================================
// Suggestions Panel
// ============================================================================

interface SuggestionsPanelProps {
  suggestions: string[];
  onApply?: (suggestion: string) => void;
  className?: string;
}

export function SuggestionsPanel({ suggestions, onApply, className = '' }: SuggestionsPanelProps) {
  const { t } = useI18n();
  if (suggestions.length === 0) return null;

  return (
    <div className={`rounded-rams-sm border border-rams-line bg-rams-panel p-4 ${className}`}>
      <div className="flex items-center gap-2 text-rams-steel">
        <LightbulbIcon />
        <span className="font-medium">
          {t('emailDrafting.suggestions.title', { count: suggestions.length, عدد: suggestions.length })}
        </span>
      </div>
      <ul className="mt-2 list-disc space-y-2 pl-5">
        {suggestions.map((suggestion, index) => (
          <li
            key={index}
            className="flex items-start justify-between gap-2 text-sm text-rams-steel"
          >
            <span>{suggestion}</span>
            {onApply && (
              <button
                type="button"
                onClick={() => onApply(suggestion)}
                className="whitespace-nowrap text-xs font-medium text-rams-steel hover:underline"
              >
                {t('emailDrafting.actions.apply')}
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ============================================================================
// Alternative Subjects
// ============================================================================

interface AlternativeSubjectsProps {
  alternatives: string[];
  onSelect: (subject: string) => void;
  className?: string;
}

export function AlternativeSubjects({
  alternatives,
  onSelect,
  className = '',
}: AlternativeSubjectsProps) {
  const { t } = useI18n();
  if (alternatives.length === 0) return null;

  return (
    <div className={`space-y-2 ${className}`}>
      <span className="text-xs font-medium text-rams-muted">
        {t('emailDrafting.alternatives.title')}
      </span>
      <div className="flex flex-wrap gap-2">
        {alternatives.map((alt, index) => (
          <button
            key={index}
            type="button"
            onClick={() => {
              // Extract just the subject part
              const subject = alt.replace(/^[^:]+:\s*/, '');
              onSelect(subject);
            }}
            className="rounded-rams-sm border border-rams-line bg-rams-panel px-3 py-1 text-sm text-rams-foreground hover:border-rams-steel"
          >
            {alt.replace(/^[^:]+:\s*/, '')}
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Email Composer
// ============================================================================

interface EmailComposerProps {
  initialRecipient?: Recipient;
  initialPurpose?: EmailPurpose;
  referenceNumber?: string;
  initialThreadEntityType?: string;
  initialThreadEntityId?: string;
  onClose?: () => void;
  onSend?: (draft: GeneratedDraft) => void;
  className?: string;
}

interface CommonThreadTrace {
  root_entity_type: string;
  root_entity_id: string;
  nodes: { entity_type: string; entity_id: string; reasoning_ids: string[] }[];
  edges: { source_entity_type: string; source_entity_id: string; target_entity_type: string; target_entity_id: string; relationship_type: string }[];
}

export function EmailComposer({
  initialRecipient,
  initialPurpose,
  referenceNumber,
  initialThreadEntityType,
  initialThreadEntityId,
  onClose,
  onSend,
  className = '',
}: EmailComposerProps) {
  const { t } = useI18n();
  const { user } = useAuthStore();
  const {
    isGenerating,
    generationError,
    recentRecipients,
    selectedTone,
    selectedLanguage,
    generateDraft,
    setSelectedTone,
    setSelectedLanguage,
  } = useEmailDraftingStore();

  const [recipientEmail, setRecipientEmail] = useState(initialRecipient?.email || '');
  const [recipientName, setRecipientName] = useState(initialRecipient?.name || '');
  const [purpose, setPurpose] = useState<EmailPurpose | null>(initialPurpose || null);
  const [keyPoints, setKeyPoints] = useState<string[]>([]);
  const [subjectHint, setSubjectHint] = useState('');
  const [refNumber, setRefNumber] = useState(referenceNumber || '');
  const [threadEntityType, setThreadEntityType] = useState(initialThreadEntityType || '');
  const [threadEntityId, setThreadEntityId] = useState(initialThreadEntityId || '');
  const [threadTrace, setThreadTrace] = useState<CommonThreadTrace | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [isTraceLoading, setIsTraceLoading] = useState(false);
  const [senderName, setSenderName] = useState('');
  const [senderEmail, setSenderEmail] = useState('');
  const [senderTitle, setSenderTitle] = useState('');
  const [companyName, setCompanyName] = useState('');

  const [draft, setDraft] = useState<GeneratedDraft | null>(null);
  const [copied, setCopied] = useState(false);
  const threadEntityOptions = useMemo(
    () => [
      { value: 'rfq', label: t('emailDrafting.thread.entityType.rfq') },
      { value: 'quote', label: t('emailDrafting.thread.entityType.quote') },
      { value: 'work_order', label: t('emailDrafting.thread.entityType.workOrder') },
      { value: 'opportunity', label: t('emailDrafting.thread.entityType.opportunity') },
      { value: 'non_conformance', label: t('emailDrafting.thread.entityType.nonConformance') },
      { value: 'shipment', label: t('emailDrafting.thread.entityType.shipment') },
      { value: 'invoice', label: t('emailDrafting.thread.entityType.invoice') },
    ],
    [t]
  );

  useEffect(() => {
    if (!user) return;
    const displayName = user.full_name || user.email;
    setSenderName((current) => current || displayName);
    setSenderEmail((current) => current || user.email || '');
    setSenderTitle((current) => current || user.job_title || '');
  }, [user]);

  useEffect(() => {
    const fetchTrace = async () => {
      if (!threadEntityType || !threadEntityId) {
        setThreadTrace(null);
        setTraceError(null);
        return;
      }
      setIsTraceLoading(true);
      setTraceError(null);
      try {
        const trace = await apiClient.get<CommonThreadTrace>(
          `/common-thread/trace?entity_type=${encodeURIComponent(threadEntityType)}&entity_id=${encodeURIComponent(threadEntityId)}`
        );
        setThreadTrace(trace);
      } catch (error) {
        setTraceError(
          error instanceof Error ? error.message : t('emailDrafting.thread.loadFailed')
        );
        setThreadTrace(null);
      } finally {
        setIsTraceLoading(false);
      }
    };

    fetchTrace();
  }, [threadEntityType, threadEntityId]);

  const handleGenerate = useCallback(async () => {
    if (!purpose || !recipientEmail || !threadEntityType || !threadEntityId) return;

    const recipient = createRecipient(recipientEmail, recipientName);
    recipient.languagePreference = selectedLanguage;
    const existingReasoningId = threadTrace?.nodes?.[0]?.reasoning_ids?.[0];

    const request: GenerationRequest = {
      id: generateId(),
      context: {
        purpose,
        recipient,
        subjectHint: subjectHint || undefined,
        keyPoints,
        attachments: [],
        referenceNumber: refNumber || undefined,
        tone: selectedTone,
        language: selectedLanguage,
        includeSignature: true,
        maxParagraphs: 4,
        threadEntityType: threadEntityType || undefined,
        threadEntityId: threadEntityId || undefined,
      },
      senderName: senderName || t('emailDrafting.defaults.senderName'),
      senderEmail: senderEmail || t('emailDrafting.defaults.senderEmail'),
      senderTitle: senderTitle || undefined,
      companyName: companyName || t('emailDrafting.defaults.companyName'),
      requestedAt: new Date(),
      threadContext: {
        entityType: threadEntityType || undefined,
        entityId: threadEntityId || undefined,
        reasoningId: existingReasoningId,
      },
    };

    const newDraft = await generateDraft(request);
    setDraft(newDraft);
  }, [
    purpose,
    recipientEmail,
    recipientName,
    keyPoints,
    subjectHint,
    refNumber,
    selectedTone,
    selectedLanguage,
    senderName,
    senderEmail,
    senderTitle,
    companyName,
    threadEntityType,
    threadEntityId,
    threadTrace,
    t,
    generateDraft,
  ]);

  const handleCopy = useCallback(() => {
    if (!draft) return;
    navigator.clipboard.writeText(draft.bodyPlain);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [draft]);

  const handleSelectRecent = useCallback((recipient: Recipient) => {
    setRecipientEmail(recipient.email);
    setRecipientName(recipient.name || '');
  }, []);

  const handleSelectAlternativeSubject = useCallback(
    (subject: string) => {
      if (!draft) return;
      setDraft({ ...draft, subject });
    },
    [draft]
  );

  const canGenerate = useMemo(() => {
    return (
      !!purpose &&
      !!recipientEmail &&
      !!threadEntityType &&
      !!threadEntityId &&
      validateRecipient({ email: recipientEmail }).length === 0
    );
  }, [purpose, recipientEmail, threadEntityType, threadEntityId]);

  return (
    <ErrorBoundary>
      <div className={`flex h-full flex-col bg-rams-chassis ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-rams-line bg-rams-panel px-6 py-4">
          <div className="flex items-center gap-2">
            <SparklesIcon />
            <h2 className="text-lg font-black uppercase text-rams-foreground">{t('emailDrafting.title')}</h2>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-rams-sm p-2 text-rams-muted hover:bg-rams-panel hover:text-rams-foreground"
              aria-label={t('emailDrafting.aria.close')}
            >
              <XIcon />
            </button>
          )}
        </div>

        <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Configuration */}
        <div className="w-1/2 overflow-y-auto border-r border-rams-line bg-rams-module p-6">
          <div className="space-y-6">
            {/* Recipient */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.recipient')}
              </label>
              <RecipientInput
                value={recipientEmail}
                name={recipientName}
                onEmailChange={setRecipientEmail}
                onNameChange={setRecipientName}
                recentRecipients={recentRecipients}
                onSelectRecent={handleSelectRecent}
              />
            </div>

            {/* Purpose */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.purpose')}
              </label>
              <PurposeSelector value={purpose} onChange={setPurpose} />
            </div>

            {/* Sender */}
            <div className="rounded-rams-sm border border-rams-line bg-rams-module p-4">
              <label className="mb-3 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.sender')}
              </label>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-rams-muted">
                    {t('emailDrafting.fields.senderName')}
                  </label>
                  <input
                    type="text"
                    value={senderName}
                    onChange={(e) => setSenderName(e.target.value)}
                    placeholder={t('emailDrafting.placeholders.senderName')}
                    className="w-full rounded-rams-sm border border-rams-line px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-rams-muted">
                    {t('emailDrafting.fields.senderEmail')}
                  </label>
                  <input
                    type="email"
                    value={senderEmail}
                    onChange={(e) => setSenderEmail(e.target.value)}
                    placeholder={t('emailDrafting.placeholders.senderEmail')}
                    className="w-full rounded-rams-sm border border-rams-line px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-rams-muted">
                    {t('emailDrafting.fields.senderTitle')}
                  </label>
                  <input
                    type="text"
                    value={senderTitle}
                    onChange={(e) => setSenderTitle(e.target.value)}
                    placeholder={t('emailDrafting.placeholders.senderTitle')}
                    className="w-full rounded-rams-sm border border-rams-line px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-rams-muted">
                    {t('emailDrafting.fields.companyName')}
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder={t('emailDrafting.placeholders.companyName')}
                    className="w-full rounded-rams-sm border border-rams-line px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
                  />
                </div>
              </div>
            </div>

            {/* Thread Context */}
            <div className="rounded-rams-sm border border-rams-line bg-rams-module p-4">
              <label className="mb-3 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.threadContext')}
              </label>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-rams-muted">
                    {t('emailDrafting.fields.threadEntityType')}
                  </label>
                  <select
                    value={threadEntityType}
                    onChange={(e) => setThreadEntityType(e.target.value)}
                    className="w-full rounded-rams-sm border border-rams-line px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
                  >
                    <option value="">{t('emailDrafting.placeholders.threadEntityType')}</option>
                    {threadEntityOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-rams-muted">
                    {t('emailDrafting.fields.threadEntityId')}
                  </label>
                  <input
                    type="text"
                    value={threadEntityId}
                    onChange={(e) => setThreadEntityId(e.target.value)}
                    placeholder={t('emailDrafting.placeholders.threadEntityId')}
                    className="w-full rounded-rams-sm border border-rams-line px-3 py-2 text-sm focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
                  />
                </div>
              </div>
              <div className="mt-3 text-xs text-rams-muted">
                {t('emailDrafting.thread.helper')}
              </div>
              {(threadEntityType && threadEntityId) && (
                <div className="mt-3 rounded-rams-sm border border-rams-line bg-rams-panel p-3 text-xs text-rams-muted">
                  {isTraceLoading && <div>{t('emailDrafting.thread.loading')}</div>}
                  {!isTraceLoading && traceError && <div className="text-rams-red">{traceError}</div>}
                  {!isTraceLoading && !traceError && threadTrace && (
                    <div className="space-y-1">
                      <div className="font-medium text-rams-foreground">{t('emailDrafting.thread.traceTitle')}</div>
                      <div>
                        {t('emailDrafting.thread.traceStats', {
                          nodes: threadTrace.nodes.length,
                          edges: threadTrace.edges.length,
                          عقد: threadTrace.nodes.length,
                          روابط: threadTrace.edges.length,
                        })}
                      </div>
                      {draft?.reasoningId && (
                        <div>
                          {t('emailDrafting.thread.reasoningId', {
                            id: draft.reasoningId,
                            معرف: draft.reasoningId,
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Reference Number */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.fields.referenceNumberOptional')}
              </label>
              <input
                type="text"
                value={refNumber}
                onChange={(e) => setRefNumber(e.target.value)}
                placeholder={t('emailDrafting.placeholders.referenceNumber')}
                className="w-full rounded-rams-sm border border-rams-line px-4 py-2 focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
              />
            </div>

            {/* Subject Hint */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.fields.subjectHintOptional')}
              </label>
              <input
                type="text"
                value={subjectHint}
                onChange={(e) => setSubjectHint(e.target.value)}
                placeholder={t('emailDrafting.placeholders.subjectHint')}
                className="w-full rounded-rams-sm border border-rams-line px-4 py-2 focus:border-rams-steel focus:outline-none focus:ring-2 focus:ring-rams-steel/20"
              />
            </div>

            {/* Tone */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.tone')}
              </label>
              <ToneSelector value={selectedTone} onChange={setSelectedTone} />
            </div>

            {/* Language */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.language')}
              </label>
              <LanguageSelector value={selectedLanguage} onChange={setSelectedLanguage} />
            </div>

            {/* Key Points */}
            <div>
              <label className="mb-2 block text-sm font-black uppercase text-rams-foreground">
                {t('emailDrafting.sections.keyPoints')}
              </label>
              <KeyPointsEditor points={keyPoints} onChange={setKeyPoints} />
            </div>

            {/* Generate Button */}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!canGenerate || isGenerating}
              className="flex w-full items-center justify-center gap-2 rounded-rams-sm bg-rams-steel px-4 py-3 font-medium text-rams-foreground transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:bg-rams-panel disabled:text-rams-muted"
            >
              {isGenerating ? (
                <>
                  <RefreshIcon />
                  {t('emailDrafting.actions.generating')}
                </>
              ) : (
                <>
                  <SparklesIcon />
                  {t('emailDrafting.actions.generateDraft')}
                </>
              )}
            </button>

            {generationError && (
              <div className="rounded-rams-sm border border-rams-line bg-rams-panel p-3 text-sm text-rams-red">
                {generationError}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex w-1/2 flex-col overflow-y-auto bg-rams-module p-6">
          {draft ? (
            <div className="space-y-4">
              <DraftPreview
                draft={draft}
                onEdit={(field) => {
                  // Focus the relevant field for editing
                  if (field === 'subject') {
                    setSubjectHint(draft.subject);
                  }
                }}
                onCopy={handleCopy}
              />

              {copied && (
                <div className="rounded-rams-sm border border-rams-line bg-rams-panel p-2 text-center text-sm text-rams-green">
                  {t('emailDrafting.notifications.copied')}
                </div>
              )}

              <AlternativeSubjects
                alternatives={draft.alternatives}
                onSelect={handleSelectAlternativeSubject}
              />

              <CompliancePanel issues={draft.complianceIssues} />

              <SuggestionsPanel suggestions={draft.suggestions} />

              {/* Action Buttons */}
              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={handleGenerate}
                  className="flex flex-1 items-center justify-center gap-2 rounded-rams-sm border border-rams-line bg-rams-panel px-4 py-2 font-medium text-rams-foreground hover:bg-rams-module"
                >
                  <RefreshIcon />
                  {t('emailDrafting.actions.regenerate')}
                </button>
                <button
                  type="button"
                  onClick={() => onSend?.(draft)}
                  className="flex flex-1 items-center justify-center gap-2 rounded-rams-sm bg-rams-green px-4 py-2 font-medium text-rams-foreground hover:opacity-90"
                >
                  <SendIcon />
                  {t('emailDrafting.actions.send')}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <div className="mb-4 rounded-rams-sm bg-rams-panel p-4">
                <MailIcon />
              </div>
              <h3 className="text-lg font-medium text-rams-foreground">{t('emailDrafting.empty.title')}</h3>
              <p className="mt-1 text-sm text-rams-muted">{t('emailDrafting.empty.description')}</p>
            </div>
          )}
        </div>
      </div>
      </div>
    </ErrorBoundary>
  );
}

// ============================================================================
// Email Drafts List
// ============================================================================

interface DraftListItemProps {
  draft: GeneratedDraft;
  isActive: boolean;
  onClick: () => void;
}

export function DraftListItem({ draft, isActive, onClick }: DraftListItemProps) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-rams-sm border p-3 text-left transition-colors ${
        isActive
          ? 'border-rams-steel bg-rams-panel'
          : 'border-rams-line bg-rams-module hover:border-rams-border hover:bg-rams-panel'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="truncate font-medium text-rams-foreground">{draft.subject}</div>
          <div className="mt-1 truncate text-sm text-rams-muted">
            {t('emailDrafting.drafts.snippet', {
              snippet: draft.bodyPlain.substring(0, 100),
              مقتطف: draft.bodyPlain.substring(0, 100),
            })}
          </div>
        </div>
        <div
          className={`ml-2 rounded-rams-sm border border-rams-line bg-rams-panel px-2 py-0.5 text-xs font-medium ${getStatusColorClass(
            draft.status
          )}`}
        >
          {t(getStatusLabelKey(draft.status))}
        </div>
      </div>
      <div className="mt-2 text-xs text-rams-muted">
        {draft.createdAt.toLocaleString()}
      </div>
    </button>
  );
}

interface DraftsListProps {
  className?: string;
}

export function DraftsList({ className = '' }: DraftsListProps) {
  const { t } = useI18n();
  const { drafts, activeDraftId, setActiveDraft } = useEmailDraftingStore();

  const draftArray = useMemo(() => Array.from(drafts.values()), [drafts]);

  if (draftArray.length === 0) {
    return (
      <div className={`rounded-rams-sm border border-rams-line bg-rams-module p-6 text-center ${className}`}>
        <MailIcon />
        <p className="mt-2 text-sm text-rams-muted">{t('emailDrafting.empty.list')}</p>
      </div>
    );
  }

  return (
    <div
      className={`space-y-2 ${className}`}
      role="list"
      aria-label={t('emailDrafting.aria.draftsList')}
    >
      {draftArray.map((draft) => (
        <DraftListItem
          key={draft.id}
          draft={draft}
          isActive={draft.id === activeDraftId}
          onClick={() => setActiveDraft(draft.id)}
        />
      ))}
    </div>
  );
}

export default EmailComposer;
