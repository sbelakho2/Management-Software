'use client';

/**
 * Correction UI Components
 * 
 * One-tap "Correct this" button and correction modal for user feedback.
 * Implements the Correction UI requirement from the Automated Feedback Loops system.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';

// =============================================================================
// Types
// =============================================================================

export type CorrectionType = 
  | 'text_edit'
  | 'field_value'
  | 'classification'
  | 'extraction'
  | 'formatting'
  | 'rejection';

export type ContextType =
  | 'rfq_parsing'
  | 'email_draft'
  | 'a3_generation'
  | 'document_classification'
  | 'entity_extraction'
  | 'summarization'
  | 'translation'
  | 'general';

export interface CorrectionRequest {
  inputText: string;
  aiOutput: string;
  userCorrection: string;
  correctionType: CorrectionType;
  contextType: ContextType;
  fieldName?: string;
  confidence?: number;
  metadata?: Record<string, unknown>;
}

export interface CorrectionResponse {
  id: string;
  status: 'success' | 'error';
  message?: string;
}

export interface CorrectionButtonProps {
  /** The original input text that was sent to AI */
  inputText: string;
  /** The AI-generated output */
  aiOutput: string;
  /** Context type for this correction */
  contextType: ContextType;
  /** Optional field name being corrected */
  fieldName?: string;
  /** Handler for submitting the correction */
  onSubmit: (correction: CorrectionRequest) => Promise<CorrectionResponse>;
  /** Optional callback after successful submission */
  onSuccess?: (response: CorrectionResponse) => void;
  /** Optional callback after failed submission */
  onError?: (error: Error) => void;
  /** Button variant */
  variant?: 'inline' | 'icon' | 'text';
  /** Additional class name */
  className?: string;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Custom button text (for 'text' variant) */
  buttonText?: string;
  /** Aria label for accessibility */
  ariaLabel?: string;
}

export interface CorrectionModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Handler to close the modal */
  onClose: () => void;
  /** The original input text */
  inputText: string;
  /** The AI-generated output */
  aiOutput: string;
  /** Context type */
  contextType: ContextType;
  /** Optional field name */
  fieldName?: string;
  /** Handler for submitting */
  onSubmit: (correction: CorrectionRequest) => Promise<CorrectionResponse>;
  /** Optional success callback */
  onSuccess?: (response: CorrectionResponse) => void;
  /** Optional error callback */
  onError?: (error: Error) => void;
}

export interface InlineCorrectionProps {
  /** The current value (AI output) */
  value: string;
  /** The original input */
  inputText: string;
  /** Context type */
  contextType: ContextType;
  /** Field name */
  fieldName: string;
  /** Handler for submitting */
  onSubmit: (correction: CorrectionRequest) => Promise<CorrectionResponse>;
  /** Whether editing is enabled */
  editable?: boolean;
  /** Callback when value is corrected */
  onChange?: (newValue: string) => void;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Icons
// =============================================================================

const PencilIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg 
    className={className} 
    fill="none" 
    stroke="currentColor" 
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" 
    />
  </svg>
);

const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg 
    className={className} 
    fill="none" 
    stroke="currentColor" 
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M5 13l4 4L19 7" 
    />
  </svg>
);

const XIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg 
    className={className} 
    fill="none" 
    stroke="currentColor" 
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M6 18L18 6M6 6l12 12" 
    />
  </svg>
);

const SpinnerIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg 
    className={`animate-spin ${className}`} 
    fill="none" 
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <circle 
      className="opacity-25" 
      cx="12" 
      cy="12" 
      r="10" 
      stroke="currentColor" 
      strokeWidth="4"
    />
    <path 
      className="opacity-75" 
      fill="currentColor" 
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Infer the correction type based on context and change.
 */
export function inferCorrectionType(
  original: string,
  corrected: string,
  contextType: ContextType,
  fieldName?: string
): CorrectionType {
  // Full rejection
  if (corrected.trim() === '' || corrected.toLowerCase() === 'reject') {
    return 'rejection';
  }
  
  // Field value correction
  if (fieldName) {
    return 'field_value';
  }
  
  // Context-based inference
  switch (contextType) {
    case 'document_classification':
      return 'classification';
    case 'entity_extraction':
      return 'extraction';
    case 'email_draft':
    case 'a3_generation':
    case 'summarization':
      return 'text_edit';
    default:
      // Check if it looks like a formatting change
      const normalizedOriginal = original.toLowerCase().replace(/\s+/g, ' ').trim();
      const normalizedCorrected = corrected.toLowerCase().replace(/\s+/g, ' ').trim();
      if (normalizedOriginal === normalizedCorrected) {
        return 'formatting';
      }
      return 'text_edit';
  }
}

/**
 * Calculate a simple confidence score based on correction length ratio.
 */
export function calculateConfidence(original: string, corrected: string): number {
  if (!original || !corrected) return 0.5;
  
  const lengthRatio = Math.min(original.length, corrected.length) / 
                      Math.max(original.length, corrected.length);
  
  // High ratio = small change = high confidence
  // Low ratio = large change = potentially lower confidence
  return Math.max(0.5, lengthRatio);
}

// =============================================================================
// CorrectionButton Component
// =============================================================================

/**
 * One-tap "Correct this" button component.
 * Opens a correction modal when clicked.
 */
export const CorrectionButton: React.FC<CorrectionButtonProps> = ({
  inputText,
  aiOutput,
  contextType,
  fieldName,
  onSubmit,
  onSuccess,
  onError,
  variant = 'inline',
  className = '',
  disabled = false,
  buttonText = 'Correct this',
  ariaLabel = 'Correct this AI output',
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  const handleClick = useCallback(() => {
    if (!disabled) {
      setIsModalOpen(true);
    }
  }, [disabled]);
  
  const handleClose = useCallback(() => {
    setIsModalOpen(false);
  }, []);
  
  const handleSuccess = useCallback((response: CorrectionResponse) => {
    setIsModalOpen(false);
    onSuccess?.(response);
  }, [onSuccess]);
  
  const baseClasses = 'inline-flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantClasses: Record<string, string> = {
    inline: 'px-2 py-1 text-xs rounded border border-gray-300 hover:bg-gray-100 focus:ring-blue-500',
    icon: 'p-1 rounded-full hover:bg-gray-100 focus:ring-blue-500',
    text: 'text-sm text-blue-600 hover:text-blue-800 hover:underline focus:ring-blue-500',
  };
  
  const disabledClasses = disabled 
    ? 'opacity-50 cursor-not-allowed' 
    : 'cursor-pointer';
  
  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        className={`${baseClasses} ${variantClasses[variant]} ${disabledClasses} ${className}`}
        aria-label={ariaLabel}
        data-testid="correction-button"
      >
        {variant === 'icon' ? (
          <PencilIcon className="w-4 h-4" />
        ) : variant === 'text' ? (
          buttonText
        ) : (
          <>
            <PencilIcon className="w-3 h-3 mr-1" />
            {buttonText}
          </>
        )}
      </button>
      
      <CorrectionModal
        isOpen={isModalOpen}
        onClose={handleClose}
        inputText={inputText}
        aiOutput={aiOutput}
        contextType={contextType}
        fieldName={fieldName}
        onSubmit={onSubmit}
        onSuccess={handleSuccess}
        onError={onError}
      />
    </>
  );
};

// =============================================================================
// CorrectionModal Component
// =============================================================================

/**
 * Modal for entering and submitting corrections.
 */
export const CorrectionModal: React.FC<CorrectionModalProps> = ({
  isOpen,
  onClose,
  inputText,
  aiOutput,
  contextType,
  fieldName,
  onSubmit,
  onSuccess,
  onError,
}) => {
  const [correction, setCorrection] = useState(aiOutput);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(0.9);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  
  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setCorrection(aiOutput);
      setError(null);
      setConfidence(0.9);
      
      // Focus textarea after modal opens
      setTimeout(() => {
        textareaRef.current?.focus();
        textareaRef.current?.select();
      }, 100);
    }
  }, [isOpen, aiOutput]);
  
  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, isSubmitting, onClose]);
  
  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        isOpen && 
        !isSubmitting && 
        modalRef.current && 
        !modalRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, isSubmitting, onClose]);
  
  const handleSubmit = useCallback(async () => {
    if (correction === aiOutput) {
      setError('Please make a correction before submitting.');
      return;
    }
    
    if (!correction.trim()) {
      setError('Correction cannot be empty. To reject, please describe why.');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const correctionType = inferCorrectionType(aiOutput, correction, contextType, fieldName);
      
      const request: CorrectionRequest = {
        inputText,
        aiOutput,
        userCorrection: correction,
        correctionType,
        contextType,
        fieldName,
        confidence,
      };
      
      const response = await onSubmit(request);
      
      if (response.status === 'success') {
        onSuccess?.(response);
      } else {
        throw new Error(response.message || 'Correction submission failed');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error.message);
      onError?.(error);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    correction,
    aiOutput,
    inputText,
    contextType,
    fieldName,
    confidence,
    onSubmit,
    onSuccess,
    onError,
  ]);
  
  const handleReject = useCallback(async () => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      const request: CorrectionRequest = {
        inputText,
        aiOutput,
        userCorrection: '[REJECTED]',
        correctionType: 'rejection',
        contextType,
        fieldName,
        confidence: 1.0,
      };
      
      const response = await onSubmit(request);
      
      if (response.status === 'success') {
        onSuccess?.(response);
      } else {
        throw new Error(response.message || 'Rejection submission failed');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error.message);
      onError?.(error);
    } finally {
      setIsSubmitting(false);
    }
  }, [inputText, aiOutput, contextType, fieldName, onSubmit, onSuccess, onError]);
  
  if (!isOpen) {
    return null;
  }
  
  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="correction-modal-title"
      data-testid="correction-modal"
    >
      <div className="flex min-h-screen items-center justify-center p-4">
        <div 
          ref={modalRef}
          className="relative w-full max-w-lg rounded-lg bg-white shadow-xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b p-4">
            <h2 
              id="correction-modal-title"
              className="text-lg font-semibold text-gray-900"
            >
              Correct AI Output
            </h2>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-full p-1 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close modal"
            >
              <XIcon className="h-5 w-5 text-gray-500" />
            </button>
          </div>
          
          {/* Content */}
          <div className="p-4 space-y-4">
            {/* Original input preview */}
            {inputText && (
              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700">
                  Original Input
                </label>
                <div className="rounded-md bg-gray-50 p-2 text-sm text-gray-600 max-h-20 overflow-y-auto">
                  {inputText.length > 200 ? `${inputText.slice(0, 200)}...` : inputText}
                </div>
              </div>
            )}
            
            {/* AI output (current value) */}
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">
                AI Output (Incorrect)
              </label>
              <div className="rounded-md bg-red-50 p-2 text-sm text-gray-700 max-h-24 overflow-y-auto">
                {aiOutput}
              </div>
            </div>
            
            {/* Correction input */}
            <div className="space-y-1">
              <label 
                htmlFor="correction-input"
                className="block text-sm font-medium text-gray-700"
              >
                Your Correction
              </label>
              <textarea
                ref={textareaRef}
                id="correction-input"
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
                disabled={isSubmitting}
                className="w-full rounded-md border border-gray-300 p-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 min-h-[100px]"
                placeholder="Enter the correct value..."
                data-testid="correction-input"
              />
            </div>
            
            {/* Confidence slider */}
            <div className="space-y-1">
              <label 
                htmlFor="confidence-slider"
                className="block text-sm font-medium text-gray-700"
              >
                Confidence: {Math.round(confidence * 100)}%
              </label>
              <input
                type="range"
                id="confidence-slider"
                min="0.5"
                max="1"
                step="0.1"
                value={confidence}
                onChange={(e) => setConfidence(parseFloat(e.target.value))}
                disabled={isSubmitting}
                className="w-full"
                data-testid="confidence-slider"
              />
            </div>
            
            {/* Error message */}
            {error && (
              <div 
                className="rounded-md bg-red-50 p-3 text-sm text-red-700"
                role="alert"
                data-testid="correction-error"
              >
                {error}
              </div>
            )}
          </div>
          
          {/* Footer */}
          <div className="flex items-center justify-between border-t p-4">
            <button
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              className="rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
              data-testid="reject-button"
            >
              {isSubmitting ? (
                <SpinnerIcon className="h-4 w-4" />
              ) : (
                'Reject Entirely'
              )}
            </button>
            
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting || correction === aiOutput}
                className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                data-testid="submit-button"
              >
                {isSubmitting ? (
                  <>
                    <SpinnerIcon className="mr-2 h-4 w-4" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <CheckIcon className="mr-1 h-4 w-4" />
                    Submit Correction
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// InlineCorrection Component
// =============================================================================

/**
 * Inline editable field with correction support.
 * Click to edit, with automatic correction submission on blur.
 */
export const InlineCorrection: React.FC<InlineCorrectionProps> = ({
  value,
  inputText,
  contextType,
  fieldName,
  onSubmit,
  editable = true,
  onChange,
  className = '',
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasBeenCorrected, setHasBeenCorrected] = useState(false);
  
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Update edit value when prop changes
  useEffect(() => {
    setEditValue(value);
  }, [value]);
  
  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);
  
  const handleStartEdit = useCallback(() => {
    if (editable && !isSubmitting) {
      setIsEditing(true);
    }
  }, [editable, isSubmitting]);
  
  const handleCancel = useCallback(() => {
    setEditValue(value);
    setIsEditing(false);
  }, [value]);
  
  const handleSave = useCallback(async () => {
    if (editValue === value) {
      setIsEditing(false);
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const correctionType = inferCorrectionType(value, editValue, contextType, fieldName);
      
      const request: CorrectionRequest = {
        inputText,
        aiOutput: value,
        userCorrection: editValue,
        correctionType,
        contextType,
        fieldName,
        confidence: calculateConfidence(value, editValue),
      };
      
      const response = await onSubmit(request);
      
      if (response.status === 'success') {
        setHasBeenCorrected(true);
        onChange?.(editValue);
      } else {
        // Revert on error
        setEditValue(value);
      }
    } catch {
      // Revert on error
      setEditValue(value);
    } finally {
      setIsSubmitting(false);
      setIsEditing(false);
    }
  }, [editValue, value, inputText, contextType, fieldName, onSubmit, onChange]);
  
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  }, [handleSave, handleCancel]);
  
  const baseClasses = 'inline-block px-2 py-1 rounded';
  const editableClasses = editable ? 'cursor-pointer hover:bg-gray-100' : '';
  const correctedClasses = hasBeenCorrected ? 'bg-green-50 border-green-200' : '';
  
  if (isEditing) {
    return (
      <span className={`${baseClasses} ${className}`}>
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          disabled={isSubmitting}
          className="w-full min-w-[100px] rounded border border-blue-500 px-1 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          data-testid="inline-correction-input"
        />
        {isSubmitting && (
          <SpinnerIcon className="ml-1 inline-block h-3 w-3" />
        )}
      </span>
    );
  }
  
  return (
    <span
      onClick={handleStartEdit}
      onKeyDown={(e) => e.key === 'Enter' && handleStartEdit()}
      role={editable ? 'button' : undefined}
      tabIndex={editable ? 0 : undefined}
      className={`${baseClasses} ${editableClasses} ${correctedClasses} ${className}`}
      data-testid="inline-correction-value"
      aria-label={editable ? `Click to correct: ${value}` : undefined}
    >
      {value}
      {editable && (
        <PencilIcon className="ml-1 inline-block h-3 w-3 text-gray-400" />
      )}
    </span>
  );
};

// =============================================================================
// useCorrectionSubmit Hook
// =============================================================================

export interface UseCorrectionSubmitOptions {
  /** API endpoint for submitting corrections */
  endpoint?: string;
  /** Custom headers for the request */
  headers?: Record<string, string>;
  /** Callback after successful submission */
  onSuccess?: (response: CorrectionResponse) => void;
  /** Callback after failed submission */
  onError?: (error: Error) => void;
}

export interface UseCorrectionSubmitReturn {
  /** Submit a correction */
  submit: (correction: CorrectionRequest) => Promise<CorrectionResponse>;
  /** Whether a submission is in progress */
  isSubmitting: boolean;
  /** Last error, if any */
  error: Error | null;
  /** Last response, if any */
  lastResponse: CorrectionResponse | null;
}

/**
 * Hook for submitting corrections to the backend.
 */
export function useCorrectionSubmit(
  options: UseCorrectionSubmitOptions = {}
): UseCorrectionSubmitReturn {
  const {
    endpoint = '/api/corrections',
    headers = {},
    onSuccess,
    onError,
  } = options;
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastResponse, setLastResponse] = useState<CorrectionResponse | null>(null);
  
  const submit = useCallback(async (correction: CorrectionRequest): Promise<CorrectionResponse> => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: JSON.stringify({
          input_text: correction.inputText,
          ai_output: correction.aiOutput,
          user_correction: correction.userCorrection,
          correction_type: correction.correctionType,
          context_type: correction.contextType,
          field_name: correction.fieldName,
          confidence_score: correction.confidence ?? 0.9,
          metadata: correction.metadata,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const data = await response.json();
      const result: CorrectionResponse = {
        id: data.id,
        status: 'success',
        message: data.message,
      };
      
      setLastResponse(result);
      onSuccess?.(result);
      
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      onError?.(error);
      
      return {
        id: '',
        status: 'error',
        message: error.message,
      };
    } finally {
      setIsSubmitting(false);
    }
  }, [endpoint, headers, onSuccess, onError]);
  
  return {
    submit,
    isSubmitting,
    error,
    lastResponse,
  };
}

// =============================================================================
// CorrectionProvider Context
// =============================================================================

export interface CorrectionContextValue {
  /** Submit a correction */
  submitCorrection: (correction: CorrectionRequest) => Promise<CorrectionResponse>;
  /** Whether a submission is in progress */
  isSubmitting: boolean;
  /** Total corrections submitted in this session */
  correctionCount: number;
}

const CorrectionContext = React.createContext<CorrectionContextValue | null>(null);

export interface CorrectionProviderProps {
  children: React.ReactNode;
  /** API endpoint for submitting corrections */
  endpoint?: string;
  /** Custom headers */
  headers?: Record<string, string>;
}

/**
 * Provider component for correction functionality.
 */
export const CorrectionProvider: React.FC<CorrectionProviderProps> = ({
  children,
  endpoint,
  headers,
}) => {
  const [correctionCount, setCorrectionCount] = useState(0);
  
  const { submit, isSubmitting } = useCorrectionSubmit({
    endpoint,
    headers,
    onSuccess: () => {
      setCorrectionCount((c) => c + 1);
    },
  });
  
  const value: CorrectionContextValue = {
    submitCorrection: submit,
    isSubmitting,
    correctionCount,
  };
  
  return (
    <CorrectionContext.Provider value={value}>
      {children}
    </CorrectionContext.Provider>
  );
};

/**
 * Hook to access correction context.
 */
export function useCorrectionContext(): CorrectionContextValue {
  const context = React.useContext(CorrectionContext);
  if (!context) {
    throw new Error('useCorrectionContext must be used within a CorrectionProvider');
  }
  return context;
}

// =============================================================================
// Exports
// =============================================================================

export default {
  CorrectionButton,
  CorrectionModal,
  InlineCorrection,
  CorrectionProvider,
  useCorrectionSubmit,
  useCorrectionContext,
  inferCorrectionType,
  calculateConfidence,
};
