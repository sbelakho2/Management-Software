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

import React, { useState, useCallback, useMemo } from 'react';
import {
  useEmailDraftingStore,
  EmailTone,
  EmailPurpose,
  Language,
  DraftStatus,
  Recipient,
  GeneratedDraft,
  GenerationRequest,
  getPurposeLabel,
  getToneLabel,
  getLanguageLabel,
  getStatusLabel,
  getStatusColor,
  getConfidenceColor,
  formatConfidenceScore,
  formatGenerationTime,
  getComplianceSeverityColor,
  getSuggestionPriorityColor,
  generateId,
  createRecipient,
  validateRecipient,
} from '@/stores/email-drafting-store';
import { ErrorBoundary } from '@/components/error-boundary';

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
        className="flex w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-4 py-2 text-left hover:border-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        aria-label="Select email purpose"
        aria-expanded={isOpen}
      >
        <span className={value ? 'text-gray-900' : 'text-gray-500'}>
          {value ? getPurposeLabel(value) : 'Select purpose...'}
        </span>
        <ChevronDownIcon />
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          {purposes.map((purpose) => (
            <button
              key={purpose}
              type="button"
              onClick={() => {
                onChange(purpose);
                setIsOpen(false);
              }}
              className={`block w-full px-4 py-2 text-left hover:bg-gray-100 ${
                value === purpose ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
              }`}
            >
              {getPurposeLabel(purpose)}
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
    <div className={`flex flex-wrap gap-2 ${className}`} role="radiogroup" aria-label="Email tone">
      {tones.map((tone) => (
        <button
          key={tone}
          type="button"
          role="radio"
          aria-checked={value === tone}
          onClick={() => onChange(tone)}
          className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
            value === tone
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {getToneLabel(tone)}
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
  const languages: Language[] = ['en', 'fr', 'de', 'es', 'it', 'pt'];

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as Language)}
      className={`rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${className}`}
      aria-label="Select language"
    >
      {languages.map((lang) => (
        <option key={lang} value={lang}>
          {getLanguageLabel(lang)}
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
            placeholder="recipient@example.com"
            className={`w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 ${
              errors.length > 0 && value
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
                : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500/20'
            }`}
            aria-label="Recipient email"
            aria-invalid={errors.length > 0 && value.length > 0}
          />

          {showRecents && recentRecipients.length > 0 && (
            <div className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
              {recentRecipients.slice(0, 5).map(({ recipient }) => (
                <button
                  key={recipient.email}
                  type="button"
                  onClick={() => onSelectRecent(recipient)}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left hover:bg-gray-100"
                >
                  <UserIcon />
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {recipient.name || recipient.email}
                    </div>
                    {recipient.name && (
                      <div className="text-xs text-gray-500">{recipient.email}</div>
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
          placeholder="Name (optional)"
          className="w-40 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          aria-label="Recipient name"
        />
      </div>
      {errors.length > 0 && value && (
        <p className="text-sm text-red-600">{errors[0]}</p>
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
          placeholder="Add a key point..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          aria-label="Add key point"
        />
        <button
          type="button"
          onClick={addPoint}
          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
        >
          Add
        </button>
      </div>
      {points.length > 0 && (
        <ul className="space-y-1" aria-label="Key points list">
          {points.map((point, index) => (
            <li
              key={index}
              className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2"
            >
              <span className="text-sm text-gray-700">• {point}</span>
              <button
                type="button"
                onClick={() => removePoint(index)}
                className="text-gray-400 hover:text-red-500"
                aria-label={`Remove: ${point}`}
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
  return (
    <div className={`rounded-lg border border-gray-200 bg-white ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <MailIcon />
          <span className="font-medium text-gray-900">Draft Preview</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium"
            style={{
              backgroundColor: `${getStatusColor(draft.status)}20`,
              color: getStatusColor(draft.status),
            }}
          >
            {getStatusLabel(draft.status)}
          </div>
          <button
            type="button"
            onClick={onCopy}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            aria-label="Copy to clipboard"
          >
            <CopyIcon />
          </button>
        </div>
      </div>

      {/* Subject */}
      <div className="border-b border-gray-100 px-4 py-2">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-500">Subject: </span>
            <span className="font-medium text-gray-900">{draft.subject}</span>
          </div>
          <button
            type="button"
            onClick={() => onEdit('subject')}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Edit subject"
          >
            <EditIcon />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-4">
        <div className="whitespace-pre-wrap font-sans text-sm text-gray-700">
          {draft.bodyPlain}
        </div>
      </div>

      {/* Footer stats */}
      <div className="flex items-center justify-between border-t border-gray-100 px-4 py-2 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span
            className="flex items-center gap-1"
            style={{ color: getConfidenceColor(draft.confidenceScore) }}
          >
            Confidence: {formatConfidenceScore(draft.confidenceScore)}
          </span>
          <span>Generated in {formatGenerationTime(draft.generationTimeMs)}</span>
        </div>
        <button
          type="button"
          onClick={() => onEdit('body')}
          className="flex items-center gap-1 text-blue-600 hover:text-blue-700"
        >
          <EditIcon />
          Edit
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
  if (issues.length === 0) {
    return (
      <div className={`rounded-lg border border-green-200 bg-green-50 p-4 ${className}`}>
        <div className="flex items-center gap-2 text-green-700">
          <CheckIcon />
          <span className="font-medium">No compliance issues detected</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border border-amber-200 bg-amber-50 p-4 ${className}`}>
      <div className="flex items-center gap-2 text-amber-700">
        <AlertIcon />
        <span className="font-medium">Compliance Issues ({issues.length})</span>
      </div>
      <ul className="mt-2 space-y-1">
        {issues.map((issue, index) => (
          <li key={index} className="flex items-start gap-2 text-sm text-amber-600">
            <span className="mt-0.5">•</span>
            <span>{issue}</span>
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
  if (suggestions.length === 0) return null;

  return (
    <div className={`rounded-lg border border-blue-200 bg-blue-50 p-4 ${className}`}>
      <div className="flex items-center gap-2 text-blue-700">
        <LightbulbIcon />
        <span className="font-medium">Suggestions ({suggestions.length})</span>
      </div>
      <ul className="mt-2 space-y-2">
        {suggestions.map((suggestion, index) => (
          <li
            key={index}
            className="flex items-start justify-between gap-2 text-sm text-blue-600"
          >
            <div className="flex items-start gap-2">
              <span className="mt-0.5">•</span>
              <span>{suggestion}</span>
            </div>
            {onApply && (
              <button
                type="button"
                onClick={() => onApply(suggestion)}
                className="whitespace-nowrap text-xs font-medium text-blue-700 hover:underline"
              >
                Apply
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
  if (alternatives.length === 0) return null;

  return (
    <div className={`space-y-2 ${className}`}>
      <span className="text-xs font-medium text-gray-500">Alternative subjects:</span>
      <div className="flex flex-wrap gap-2">
        {alternatives.map((alt, index) => (
          <button
            key={index}
            type="button"
            onClick={() => {
              // Extract just the subject part
              const subject = alt.replace(/^Alternative Subject:\s*/, '');
              onSelect(subject);
            }}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1 text-sm text-gray-600 hover:border-blue-300 hover:bg-blue-50"
          >
            {alt.replace(/^Alternative Subject:\s*/, '')}
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
  onClose?: () => void;
  onSend?: (draft: GeneratedDraft) => void;
  className?: string;
}

export function EmailComposer({
  initialRecipient,
  initialPurpose,
  referenceNumber,
  onClose,
  onSend,
  className = '',
}: EmailComposerProps) {
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

  const [draft, setDraft] = useState<GeneratedDraft | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = useCallback(async () => {
    if (!purpose || !recipientEmail) return;

    const recipient = createRecipient(recipientEmail, recipientName);
    recipient.languagePreference = selectedLanguage;

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
      },
      senderName: 'Your Name',
      senderEmail: 'your.email@company.com',
      companyName: 'Your Company',
      requestedAt: new Date(),
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
    return !!purpose && !!recipientEmail && validateRecipient({ email: recipientEmail }).length === 0;
  }, [purpose, recipientEmail]);

  return (
    <ErrorBoundary>
      <div className={`flex h-full flex-col bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-2">
          <SparklesIcon />
          <h2 className="text-lg font-semibold text-gray-900">AI Email Composer</h2>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <XIcon />
          </button>
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Configuration */}
        <div className="w-1/2 overflow-y-auto border-r border-gray-200 bg-white p-6">
          <div className="space-y-6">
            {/* Recipient */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Recipient</label>
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
              <label className="mb-2 block text-sm font-medium text-gray-700">Purpose</label>
              <PurposeSelector value={purpose} onChange={setPurpose} />
            </div>

            {/* Reference Number */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Reference Number (optional)
              </label>
              <input
                type="text"
                value={refNumber}
                onChange={(e) => setRefNumber(e.target.value)}
                placeholder="e.g., RFQ-2024-001"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            {/* Subject Hint */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Subject Hint (optional)
              </label>
              <input
                type="text"
                value={subjectHint}
                onChange={(e) => setSubjectHint(e.target.value)}
                placeholder="e.g., Product Demo Discussion"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            {/* Tone */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Tone</label>
              <ToneSelector value={selectedTone} onChange={setSelectedTone} />
            </div>

            {/* Language */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Language</label>
              <LanguageSelector value={selectedLanguage} onChange={setSelectedLanguage} />
            </div>

            {/* Key Points */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Key Points</label>
              <KeyPointsEditor points={keyPoints} onChange={setKeyPoints} />
            </div>

            {/* Generate Button */}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!canGenerate || isGenerating}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {isGenerating ? (
                <>
                  <RefreshIcon />
                  Generating...
                </>
              ) : (
                <>
                  <SparklesIcon />
                  Generate Draft
                </>
              )}
            </button>

            {generationError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                {generationError}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex w-1/2 flex-col overflow-y-auto p-6">
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
                <div className="rounded-lg bg-green-100 p-2 text-center text-sm text-green-700">
                  Copied to clipboard!
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
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 hover:bg-gray-50"
                >
                  <RefreshIcon />
                  Regenerate
                </button>
                <button
                  type="button"
                  onClick={() => onSend?.(draft)}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700"
                >
                  <SendIcon />
                  Send
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <div className="mb-4 rounded-full bg-gray-100 p-4">
                <MailIcon />
              </div>
              <h3 className="text-lg font-medium text-gray-900">No Draft Yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Configure your email settings and click &quot;Generate Draft&quot; to create an
                AI-powered email.
              </p>
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
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-lg border p-3 text-left transition-colors ${
        isActive
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="truncate font-medium text-gray-900">{draft.subject}</div>
          <div className="mt-1 truncate text-sm text-gray-500">
            {draft.bodyPlain.substring(0, 100)}...
          </div>
        </div>
        <div
          className="ml-2 rounded-full px-2 py-0.5 text-xs font-medium"
          style={{
            backgroundColor: `${getStatusColor(draft.status)}20`,
            color: getStatusColor(draft.status),
          }}
        >
          {getStatusLabel(draft.status)}
        </div>
      </div>
      <div className="mt-2 text-xs text-gray-400">
        {draft.createdAt.toLocaleString()}
      </div>
    </button>
  );
}

interface DraftsListProps {
  className?: string;
}

export function DraftsList({ className = '' }: DraftsListProps) {
  const { drafts, activeDraftId, setActiveDraft } = useEmailDraftingStore();

  const draftArray = useMemo(() => Array.from(drafts.values()), [drafts]);

  if (draftArray.length === 0) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-6 text-center ${className}`}>
        <MailIcon />
        <p className="mt-2 text-sm text-gray-500">No drafts yet</p>
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`} role="list" aria-label="Email drafts">
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
