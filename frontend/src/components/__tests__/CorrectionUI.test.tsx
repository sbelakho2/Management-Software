/**
 * Tests for Correction UI Components
 */

import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  CorrectionButton,
  CorrectionModal,
  InlineCorrection,
  CorrectionProvider,
  useCorrectionSubmit,
  useCorrectionContext,
  inferCorrectionType,
  calculateConfidence,
  CorrectionRequest,
  CorrectionResponse,
} from '../CorrectionUI';
import { renderHook } from '@testing-library/react';
import { renderWithI18n } from '@/test-utils';

const render = renderWithI18n;

// =============================================================================
// Mocks
// =============================================================================

const mockSubmit = jest.fn<Promise<CorrectionResponse>, [CorrectionRequest]>();

beforeEach(() => {
  mockSubmit.mockReset();
  mockSubmit.mockResolvedValue({ id: 'corr_123', status: 'success' });
});

// Mock fetch for useCorrectionSubmit tests
const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

// =============================================================================
// Unit Tests: inferCorrectionType
// =============================================================================

describe('inferCorrectionType', () => {
  it('returns rejection for empty correction', () => {
    expect(inferCorrectionType('input', 'output', 'general', undefined)).toBe('text_edit');
    expect(inferCorrectionType('input', '', 'general', undefined)).toBe('rejection');
    expect(inferCorrectionType('input', 'reject', 'general', undefined)).toBe('rejection');
  });
  
  it('returns field_value when fieldName is provided', () => {
    expect(inferCorrectionType('input', 'output', 'rfq_parsing', 'part_number')).toBe('field_value');
  });
  
  it('returns classification for document_classification context', () => {
    expect(inferCorrectionType('input', 'output', 'document_classification', undefined)).toBe('classification');
  });
  
  it('returns extraction for entity_extraction context', () => {
    expect(inferCorrectionType('input', 'output', 'entity_extraction', undefined)).toBe('extraction');
  });
  
  it('returns text_edit for email_draft context', () => {
    expect(inferCorrectionType('input', 'output', 'email_draft', undefined)).toBe('text_edit');
  });
  
  it('returns text_edit for a3_generation context', () => {
    expect(inferCorrectionType('input', 'output', 'a3_generation', undefined)).toBe('text_edit');
  });
  
  it('returns formatting for whitespace-only changes', () => {
    expect(inferCorrectionType('Hello World', 'hello  world', 'general', undefined)).toBe('formatting');
  });
  
  it('returns text_edit for general context with content changes', () => {
    expect(inferCorrectionType('Hello', 'Goodbye', 'general', undefined)).toBe('text_edit');
  });
});

// =============================================================================
// Unit Tests: calculateConfidence
// =============================================================================

describe('calculateConfidence', () => {
  it('returns 0.5 for empty inputs', () => {
    expect(calculateConfidence('', '')).toBe(0.5);
    expect(calculateConfidence('', 'test')).toBe(0.5);
    expect(calculateConfidence('test', '')).toBe(0.5);
  });
  
  it('returns high confidence for small changes', () => {
    const confidence = calculateConfidence('Hello world', 'Hello World');
    expect(confidence).toBeGreaterThan(0.8);
  });
  
  it('returns lower confidence for large changes', () => {
    const confidence = calculateConfidence('a', 'a very long replacement text');
    expect(confidence).toBe(0.5); // Minimum is 0.5
  });
  
  it('returns 1.0 for identical strings', () => {
    const confidence = calculateConfidence('same', 'same');
    expect(confidence).toBe(1);
  });
});

// =============================================================================
// CorrectionButton Tests
// =============================================================================

describe('CorrectionButton', () => {
  const defaultProps = {
    inputText: 'Parse this RFQ',
    aiOutput: 'Part: ABC',
    contextType: 'rfq_parsing' as const,
    onSubmit: mockSubmit,
  };
  
  it('renders with default text', () => {
    render(<CorrectionButton {...defaultProps} />);
    expect(screen.getByText('Correct This')).toBeInTheDocument();
  });
  
  it('renders with custom button text', () => {
    render(<CorrectionButton {...defaultProps} buttonText="Fix this" />);
    expect(screen.getByText('Fix this')).toBeInTheDocument();
  });
  
  it('renders icon variant', () => {
    render(<CorrectionButton {...defaultProps} variant="icon" />);
    expect(screen.getByRole('button')).toBeInTheDocument();
    expect(screen.queryByText('Correct this')).not.toBeInTheDocument();
  });
  
  it('renders text variant', () => {
    render(<CorrectionButton {...defaultProps} variant="text" />);
    expect(screen.getByText('Correct This')).toBeInTheDocument();
  });
  
  it('opens modal on click', async () => {
    render(<CorrectionButton {...defaultProps} />);
    
    const button = screen.getByTestId('correction-button');
    await userEvent.click(button);
    
    expect(screen.getByTestId('correction-modal')).toBeInTheDocument();
  });
  
  it('is disabled when disabled prop is true', () => {
    render(<CorrectionButton {...defaultProps} disabled />);
    
    const button = screen.getByTestId('correction-button');
    expect(button).toBeDisabled();
  });
  
  it('does not open modal when disabled', async () => {
    render(<CorrectionButton {...defaultProps} disabled />);
    
    const button = screen.getByTestId('correction-button');
    await userEvent.click(button);
    
    expect(screen.queryByTestId('correction-modal')).not.toBeInTheDocument();
  });
  
  it('has correct aria-label', () => {
    render(<CorrectionButton {...defaultProps} ariaLabel="Custom label" />);
    expect(screen.getByLabelText('Custom label')).toBeInTheDocument();
  });
  
  it('applies custom className', () => {
    render(<CorrectionButton {...defaultProps} className="custom-class" />);
    expect(screen.getByTestId('correction-button')).toHaveClass('custom-class');
  });
});

// =============================================================================
// CorrectionModal Tests
// =============================================================================

describe('CorrectionModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    inputText: 'Parse this RFQ',
    aiOutput: 'Part: ABC',
    contextType: 'rfq_parsing' as const,
    onSubmit: mockSubmit,
  };
  
  beforeEach(() => {
    defaultProps.onClose.mockReset();
    mockSubmit.mockReset();
    mockSubmit.mockResolvedValue({ id: 'corr_123', status: 'success' });
  });
  
  it('renders when open', () => {
    render(<CorrectionModal {...defaultProps} />);
    expect(screen.getByTestId('correction-modal')).toBeInTheDocument();
  });
  
  it('does not render when closed', () => {
    render(<CorrectionModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId('correction-modal')).not.toBeInTheDocument();
  });
  
  it('displays AI output', () => {
    render(<CorrectionModal {...defaultProps} />);
    // AI output appears in the "incorrect" section
    expect(screen.getByText('Ai Output Incorrect')).toBeInTheDocument();
    // And the value appears in both the display and the textarea
    const displays = screen.getAllByText('Part: ABC');
    expect(displays.length).toBeGreaterThanOrEqual(1);
  });
  
  it('displays original input', () => {
    render(<CorrectionModal {...defaultProps} />);
    expect(screen.getByText('Original Input')).toBeInTheDocument();
    expect(screen.getByText('Parse this RFQ')).toBeInTheDocument();
  });
  
  it('has editable correction textarea', () => {
    render(<CorrectionModal {...defaultProps} />);
    const textarea = screen.getByTestId('correction-input');
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveValue('Part: ABC');
  });
  
  it('has confidence slider', () => {
    render(<CorrectionModal {...defaultProps} />);
    const slider = screen.getByTestId('confidence-slider');
    expect(slider).toBeInTheDocument();
  });
  
  it('closes when close button is clicked', async () => {
    render(<CorrectionModal {...defaultProps} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    await userEvent.click(closeButton);
    
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
  
  it('closes when cancel button is clicked', async () => {
    render(<CorrectionModal {...defaultProps} />);
    
    const cancelButton = screen.getByText('Cancel');
    await userEvent.click(cancelButton);
    
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
  
  it('closes on Escape key', async () => {
    render(<CorrectionModal {...defaultProps} />);
    
    await userEvent.keyboard('{Escape}');
    
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
  
  it('shows error when submitting without changes', async () => {
    render(<CorrectionModal {...defaultProps} />);
    
    const submitButton = screen.getByTestId('submit-button');
    expect(submitButton).toBeDisabled();
  });
  
  it('submits correction successfully', async () => {
    const onSuccess = jest.fn();
    render(<CorrectionModal {...defaultProps} onSuccess={onSuccess} />);
    
    const textarea = screen.getByTestId('correction-input');
    
    // Use fireEvent to set the value directly instead of userEvent for reliability
    fireEvent.change(textarea, { target: { value: 'Part: ABC-123' } });
    
    const submitButton = screen.getByTestId('submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          aiOutput: 'Part: ABC',
          userCorrection: 'Part: ABC-123',
          contextType: 'rfq_parsing',
        })
      );
    }, { timeout: 3000 });
    
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
  
  it('handles submission error', async () => {
    const onError = jest.fn();
    mockSubmit.mockRejectedValue(new Error('Network error'));
    
    render(<CorrectionModal {...defaultProps} onError={onError} />);
    
    const textarea = screen.getByTestId('correction-input');
    await userEvent.clear(textarea);
    await userEvent.type(textarea, 'New value');
    
    const submitButton = screen.getByTestId('submit-button');
    await userEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByTestId('correction-error')).toBeInTheDocument();
    });
    
    expect(onError).toHaveBeenCalled();
  });
  
  it('handles rejection', async () => {
    render(<CorrectionModal {...defaultProps} />);
    
    const rejectButton = screen.getByTestId('reject-button');
    await userEvent.click(rejectButton);
    
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          correctionType: 'rejection',
          userCorrection: '[REJECTED]',
        })
      );
    });
  });
  
  it('adjusts confidence with slider', async () => {
    render(<CorrectionModal {...defaultProps} />);
    
    const slider = screen.getByTestId('confidence-slider');
    fireEvent.change(slider, { target: { value: '0.7' } });
    
    expect(screen.getByText('Confidence: 70%')).toBeInTheDocument();
  });
});

// =============================================================================
// InlineCorrection Tests
// =============================================================================

describe('InlineCorrection', () => {
  const defaultProps = {
    value: 'ABC-123',
    inputText: 'Part number',
    contextType: 'rfq_parsing' as const,
    fieldName: 'part_number',
    onSubmit: mockSubmit,
  };
  
  it('displays the value', () => {
    render(<InlineCorrection {...defaultProps} />);
    expect(screen.getByText('ABC-123')).toBeInTheDocument();
  });
  
  it('shows edit icon when editable', () => {
    render(<InlineCorrection {...defaultProps} />);
    // The pencil icon should be visible
    expect(screen.getByTestId('inline-correction-value')).toBeInTheDocument();
  });
  
  it('enters edit mode on click', async () => {
    render(<InlineCorrection {...defaultProps} />);
    
    const value = screen.getByTestId('inline-correction-value');
    await userEvent.click(value);
    
    expect(screen.getByTestId('inline-correction-input')).toBeInTheDocument();
  });
  
  it('does not enter edit mode when not editable', async () => {
    render(<InlineCorrection {...defaultProps} editable={false} />);
    
    const value = screen.getByTestId('inline-correction-value');
    await userEvent.click(value);
    
    expect(screen.queryByTestId('inline-correction-input')).not.toBeInTheDocument();
  });
  
  it('saves on blur', async () => {
    render(<InlineCorrection {...defaultProps} />);
    
    const value = screen.getByTestId('inline-correction-value');
    await userEvent.click(value);
    
    const input = screen.getByTestId('inline-correction-input');
    await userEvent.clear(input);
    await userEvent.type(input, 'XYZ-789');
    
    fireEvent.blur(input);
    
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          userCorrection: 'XYZ-789',
        })
      );
    });
  });
  
  it('saves on Enter key', async () => {
    render(<InlineCorrection {...defaultProps} />);
    
    const value = screen.getByTestId('inline-correction-value');
    await userEvent.click(value);
    
    const input = screen.getByTestId('inline-correction-input');
    await userEvent.clear(input);
    await userEvent.type(input, 'XYZ-789{Enter}');
    
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalled();
    });
  });
  
  it('cancels on Escape key', async () => {
    render(<InlineCorrection {...defaultProps} />);
    
    const value = screen.getByTestId('inline-correction-value');
    await userEvent.click(value);
    
    const input = screen.getByTestId('inline-correction-input');
    await userEvent.clear(input);
    await userEvent.type(input, 'XYZ-789{Escape}');
    
    expect(screen.queryByTestId('inline-correction-input')).not.toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();
  });
  
  it('calls onChange after successful correction', async () => {
    const onChange = jest.fn();
    render(<InlineCorrection {...defaultProps} onChange={onChange} />);
    
    const value = screen.getByTestId('inline-correction-value');
    await userEvent.click(value);
    
    const input = screen.getByTestId('inline-correction-input');
    await userEvent.clear(input);
    await userEvent.type(input, 'NEW-VALUE');
    
    fireEvent.blur(input);
    
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('NEW-VALUE');
    });
  });
  
  it('applies custom className', () => {
    render(<InlineCorrection {...defaultProps} className="custom-class" />);
    expect(screen.getByTestId('inline-correction-value')).toHaveClass('custom-class');
  });
});

// =============================================================================
// useCorrectionSubmit Hook Tests
// =============================================================================

describe('useCorrectionSubmit', () => {
  it('submits correction successfully', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'corr_123', message: 'Success' }),
    });
    
    const { result } = renderHook(() => useCorrectionSubmit());
    
    let response: CorrectionResponse | undefined;
    await act(async () => {
      response = await result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(response?.status).toBe('success');
    expect(response?.id).toBe('corr_123');
    expect(result.current.lastResponse?.id).toBe('corr_123');
  });
  
  it('handles submission error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
    });
    
    const { result } = renderHook(() => useCorrectionSubmit());
    
    let response: CorrectionResponse | undefined;
    await act(async () => {
      response = await result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(response?.status).toBe('error');
    expect(result.current.error).toBeTruthy();
  });
  
  it('calls onSuccess callback', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'corr_123' }),
    });
    
    const onSuccess = jest.fn();
    const { result } = renderHook(() => useCorrectionSubmit({ onSuccess }));
    
    await act(async () => {
      await result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(onSuccess).toHaveBeenCalled();
  });
  
  it('calls onError callback', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    
    const onError = jest.fn();
    const { result } = renderHook(() => useCorrectionSubmit({ onError }));
    
    await act(async () => {
      await result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(onError).toHaveBeenCalled();
  });
  
  it('uses custom endpoint', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'corr_123' }),
    });
    
    const { result } = renderHook(() => 
      useCorrectionSubmit({ endpoint: '/api/custom/corrections' })
    );
    
    await act(async () => {
      await result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/custom/corrections',
      expect.any(Object)
    );
  });
  
  it('includes custom headers', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'corr_123' }),
    });
    
    const { result } = renderHook(() => 
      useCorrectionSubmit({ headers: { 'X-Custom': 'value' } })
    );
    
    await act(async () => {
      await result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Custom': 'value',
        }),
      })
    );
  });
  
  it('tracks isSubmitting state', async () => {
    let resolvePromise: (value: unknown) => void = () => {};
    mockFetch.mockReturnValue(new Promise((resolve) => {
      resolvePromise = resolve;
    }));
    
    const { result } = renderHook(() => useCorrectionSubmit());
    
    expect(result.current.isSubmitting).toBe(false);
    
    // Start submission
    let submitPromise: Promise<CorrectionResponse>;
    act(() => {
      submitPromise = result.current.submit({
        inputText: 'input',
        aiOutput: 'output',
        userCorrection: 'correct',
        correctionType: 'text_edit',
        contextType: 'general',
      });
    });
    
    expect(result.current.isSubmitting).toBe(true);
    
    // Complete submission
    await act(async () => {
      resolvePromise({
        ok: true,
        json: () => Promise.resolve({ id: 'corr_123' }),
      });
      await submitPromise;
    });
    
    expect(result.current.isSubmitting).toBe(false);
  });
});

// =============================================================================
// CorrectionProvider Tests
// =============================================================================

describe('CorrectionProvider', () => {
  const TestConsumer: React.FC = () => {
    const { correctionCount, isSubmitting, submitCorrection } = useCorrectionContext();
    return (
      <div>
        <span data-testid="count">{correctionCount}</span>
        <span data-testid="submitting">{isSubmitting.toString()}</span>
        <button
          onClick={() => submitCorrection({
            inputText: 'input',
            aiOutput: 'output',
            userCorrection: 'correct',
            correctionType: 'text_edit',
            contextType: 'general',
          })}
        >
          Submit
        </button>
      </div>
    );
  };
  
  it('provides context to children', () => {
    render(
      <CorrectionProvider>
        <TestConsumer />
      </CorrectionProvider>
    );
    
    expect(screen.getByTestId('count')).toHaveTextContent('0');
    expect(screen.getByTestId('submitting')).toHaveTextContent('false');
  });
  
  it('increments correction count on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'corr_123' }),
    });
    
    render(
      <CorrectionProvider>
        <TestConsumer />
      </CorrectionProvider>
    );
    
    const button = screen.getByText('Submit');
    await userEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByTestId('count')).toHaveTextContent('1');
    });
  });
  
  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => render(<TestConsumer />)).toThrow(
      'useCorrectionContext must be used within a CorrectionProvider'
    );
    
    consoleSpy.mockRestore();
  });
});

// =============================================================================
// Accessibility Tests
// =============================================================================

describe('Accessibility', () => {
  it('CorrectionButton has accessible name', () => {
    render(
      <CorrectionButton
        inputText="input"
        aiOutput="output"
        contextType="general"
        onSubmit={mockSubmit}
      />
    );
    
    expect(screen.getByRole('button')).toHaveAccessibleName();
  });
  
  it('CorrectionModal has dialog role', () => {
    render(
      <CorrectionModal
        isOpen={true}
        onClose={() => {}}
        inputText="input"
        aiOutput="output"
        contextType="general"
        onSubmit={mockSubmit}
      />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
  
  it('CorrectionModal has aria-modal', () => {
    render(
      <CorrectionModal
        isOpen={true}
        onClose={() => {}}
        inputText="input"
        aiOutput="output"
        contextType="general"
        onSubmit={mockSubmit}
      />
    );
    
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });
  
  it('Error message has alert role', async () => {
    mockSubmit.mockRejectedValue(new Error('Test error'));
    
    render(
      <CorrectionModal
        isOpen={true}
        onClose={() => {}}
        inputText="input"
        aiOutput="output"
        contextType="general"
        onSubmit={mockSubmit}
      />
    );
    
    const textarea = screen.getByTestId('correction-input');
    await userEvent.clear(textarea);
    await userEvent.type(textarea, 'New value');
    
    const submitButton = screen.getByTestId('submit-button');
    await userEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
  
  it('InlineCorrection has accessible description when editable', () => {
    render(
      <InlineCorrection
        value="test"
        inputText="input"
        contextType="general"
        fieldName="field"
        onSubmit={mockSubmit}
      />
    );
    
    expect(screen.getByTestId('inline-correction-value')).toHaveAttribute('role', 'button');
  });
});
