import { act } from 'react-dom/test-utils';

jest.mock('axios', () => {
  const isAxiosError = (error: any) => Boolean(error?.isAxiosError);

  const post = jest.fn().mockImplementation((_url: string, payload: any) => {
    const name = payload?.recipient?.name || 'there';
    const keyPoints = payload?.key_points || [];
    return Promise.resolve({
      data: {
        id: 'draft-1',
        subject: payload?.reference_number ? `Update on ${payload.reference_number}` : 'Subject',
        salutation: `Hello ${name}`,
        body: keyPoints.length ? keyPoints.join(' ') : 'Body content',
        opening: 'Opening',
        main_content: keyPoints.length ? keyPoints : ['Point 1'],
        closing: 'Regards',
        signature: 'Signature',
        alternatives: [],
        compliance_issues: [],
        suggestions: [],
        tokens_used: 0,
        generation_time_ms: 1,
        model_version: 'v1.0',
        confidence_score: 0.9,
      },
    });
  });

  const create = jest.fn(() => {
    const instance: any = jest.fn().mockResolvedValue({ data: {} });
    instance.interceptors = {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    };
    instance.post = post;
    instance.get = jest.fn().mockImplementation((url: string) => {
      if (typeof url === 'string' && url.startsWith('/common-thread/trace')) {
        return Promise.resolve({
          data: {
            root_entity_type: 'rfq',
            root_entity_id: 'RFQ-123',
            nodes: [],
            edges: [],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    instance.put = jest.fn().mockResolvedValue({ data: {} });
    instance.delete = jest.fn().mockResolvedValue({ data: {} });
    return instance;
  });

  return {
    __esModule: true,
    default: {
      create,
      post,
      isCancel: jest.fn(() => false),
      isAxiosError,
    },
    isAxiosError,
  };
});

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));
/**
 * Tests for Email Composer Components
 */

import React from 'react';
import { render as baseRender, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { I18nProvider } from '@/contexts/i18n-context';
import en from '@/locales/en.json';
import {
  EmailComposer,
  PurposeSelector,
  ToneSelector,
  LanguageSelector,
  RecipientInput,
  KeyPointsEditor,
  DraftPreview,
  CompliancePanel,
  SuggestionsPanel,
  AlternativeSubjects,
  DraftListItem,
  DraftsList,
} from '../email-composer';
import {
  useEmailDraftingStore,
  GeneratedDraft,
  Recipient,
  DraftStatus,
  formatConfidenceScore,
  formatGenerationTime,
} from '@/stores/email-drafting-store';

const getText = (key: string, params?: Record<string, string | number>): string => {
  const parts = key.split('.');
  let current: any = en;
  for (const part of parts) {
    if (!current || typeof current !== 'object') return key;
    current = current[part];
  }
  if (typeof current !== 'string') return key;
  if (!params) return current;
  return Object.entries(params).reduce((text, [param, value]) => {
    return text.replace(new RegExp(`\\{\\{?${param}\\}\\}?`, 'g'), String(value));
  }, current);
};

const render = (ui: React.ReactElement) => baseRender(<I18nProvider>{ui}</I18nProvider>);

// Reset store before each test
beforeEach(() => {
  useEmailDraftingStore.getState().reset();
});

// ============================================================================
// Purpose Selector Tests
// ============================================================================

describe('PurposeSelector', () => {
  it('should render with placeholder', () => {
    render(<PurposeSelector value={null} onChange={jest.fn()} />);
    expect(screen.getByText(getText('emailDrafting.placeholders.selectPurpose'))).toBeInTheDocument();
  });

  it('should render with selected value', () => {
    render(<PurposeSelector value="quote_followup" onChange={jest.fn()} />);
    expect(screen.getByText(getText('emailDrafting.purpose.quoteFollowup'))).toBeInTheDocument();
  });

  it('should open dropdown on click', async () => {
    const user = userEvent.setup();
    render(<PurposeSelector value={null} onChange={jest.fn()} />);

    await act(async () => {
      await user.click(screen.getByRole('button'));
    });

    expect(
      await screen.findByText(getText('emailDrafting.purpose.missingInfoRequest'))
    ).toBeInTheDocument();
    expect(
      await screen.findByText(getText('emailDrafting.purpose.quoteFollowup'))
    ).toBeInTheDocument();
    expect(
      await screen.findByText(getText('emailDrafting.purpose.meetingRequest'))
    ).toBeInTheDocument();
  });

  it('should call onChange when option selected', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<PurposeSelector value={null} onChange={onChange} />);

    await act(async () => {
      await user.click(screen.getByRole('button'));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });

    expect(onChange).toHaveBeenCalledWith('quote_followup');
  });

  it('should close dropdown after selection', async () => {
    const user = userEvent.setup();
    render(<PurposeSelector value={null} onChange={jest.fn()} />);

    await act(async () => {
      await user.click(screen.getByRole('button'));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });

    expect(
      screen.queryByText(getText('emailDrafting.purpose.missingInfoRequest'))
    ).not.toBeInTheDocument();
  });

  it('should have aria-expanded attribute', () => {
    render(<PurposeSelector value={null} onChange={jest.fn()} />);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-expanded', 'false');
  });

  it('should highlight selected option', async () => {
    const user = userEvent.setup();
    render(<PurposeSelector value="quote_followup" onChange={jest.fn()} />);

    await act(async () => {
      await user.click(screen.getByRole('button'));
    });

    // Get all elements with that text and find the one in the dropdown
    const selectedOptions = screen.getAllByText(getText('emailDrafting.purpose.quoteFollowup'));
    const dropdownOption = selectedOptions.find((el) => el.tagName === 'BUTTON');
    expect(dropdownOption).toHaveClass('bg-rams-panel', 'text-rams-steel');
  });
});

// ============================================================================
// Tone Selector Tests
// ============================================================================

describe('ToneSelector', () => {
  it('should render all tone options', () => {
    render(<ToneSelector value="professional" onChange={jest.fn()} />);

    expect(screen.getByText(getText('emailDrafting.tone.formal'))).toBeInTheDocument();
    expect(screen.getByText(getText('emailDrafting.tone.professional'))).toBeInTheDocument();
    expect(screen.getByText(getText('emailDrafting.tone.friendly'))).toBeInTheDocument();
    expect(screen.getByText(getText('emailDrafting.tone.urgent'))).toBeInTheDocument();
  });

  it('should highlight selected tone', () => {
    render(<ToneSelector value="professional" onChange={jest.fn()} />);

    const professionalButton = screen.getByText(getText('emailDrafting.tone.professional'));
    expect(professionalButton).toHaveClass('bg-rams-steel', 'text-rams-foreground');
  });

  it('should call onChange when tone clicked', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<ToneSelector value="professional" onChange={onChange} />);

    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.tone.formal')));
    });

    expect(onChange).toHaveBeenCalledWith('formal');
  });

  it('should have radio role', () => {
    render(<ToneSelector value="professional" onChange={jest.fn()} />);

    const radioGroup = screen.getByRole('radiogroup');
    expect(radioGroup).toBeInTheDocument();
  });

  it('should set aria-checked correctly', () => {
    render(<ToneSelector value="friendly" onChange={jest.fn()} />);

    const friendlyButton = screen.getByRole('radio', { name: getText('emailDrafting.tone.friendly') });
    expect(friendlyButton).toHaveAttribute('aria-checked', 'true');

    const formalButton = screen.getByRole('radio', { name: getText('emailDrafting.tone.formal') });
    expect(formalButton).toHaveAttribute('aria-checked', 'false');
  });
});

// ============================================================================
// Language Selector Tests
// ============================================================================

describe('LanguageSelector', () => {
  it('should render as select element', () => {
    render(<LanguageSelector value="en" onChange={jest.fn()} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('should have all language options', () => {
    render(<LanguageSelector value="en" onChange={jest.fn()} />);

    expect(
      screen.getByRole('option', { name: getText('emailDrafting.language.english') })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: getText('emailDrafting.language.french') })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: getText('emailDrafting.language.german') })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: getText('emailDrafting.language.spanish') })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: getText('emailDrafting.language.italian') })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: getText('emailDrafting.language.portuguese') })
    ).toBeInTheDocument();
  });

  it('should show selected language', () => {
    render(<LanguageSelector value="fr" onChange={jest.fn()} />);

    const select = screen.getByRole('combobox');
    expect(select).toHaveValue('fr');
  });

  it('should call onChange when language selected', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<LanguageSelector value="en" onChange={onChange} />);

    await user.selectOptions(screen.getByRole('combobox'), 'de');

    expect(onChange).toHaveBeenCalledWith('de');
  });

  it('should have aria-label', () => {
    render(<LanguageSelector value="en" onChange={jest.fn()} />);
    expect(
      screen.getByLabelText(getText('emailDrafting.aria.selectLanguage'))
    ).toBeInTheDocument();
  });
});

// ============================================================================
// Recipient Input Tests
// ============================================================================

describe('RecipientInput', () => {
  const defaultProps = {
    value: '',
    name: '',
    onEmailChange: jest.fn(),
    onNameChange: jest.fn(),
    recentRecipients: [],
    onSelectRecent: jest.fn(),
  };

  it('should render email and name inputs', () => {
    render(<RecipientInput {...defaultProps} />);

    expect(screen.getByLabelText(getText('emailDrafting.aria.recipientEmail'))).toBeInTheDocument();
    expect(screen.getByLabelText(getText('emailDrafting.aria.recipientName'))).toBeInTheDocument();
  });

  it('should show email placeholder', () => {
    render(<RecipientInput {...defaultProps} />);
    expect(
      screen.getByPlaceholderText(getText('emailDrafting.placeholders.recipientEmail'))
    ).toBeInTheDocument();
  });

  it('should call onEmailChange when typing email', async () => {
    const user = userEvent.setup();
    const onEmailChange = jest.fn();
    render(<RecipientInput {...defaultProps} onEmailChange={onEmailChange} />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'test@example.com'
      );
    });

    expect(onEmailChange).toHaveBeenCalled();
  });

  it('should call onNameChange when typing name', async () => {
    const user = userEvent.setup();
    const onNameChange = jest.fn();
    render(<RecipientInput {...defaultProps} onNameChange={onNameChange} />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientName')),
        'John Doe'
      );
    });

    expect(onNameChange).toHaveBeenCalled();
  });

  it('should show validation error for invalid email', () => {
    render(<RecipientInput {...defaultProps} value="notanemail" />);
    expect(screen.getByText(getText('emailDrafting.validation.emailInvalid'))).toBeInTheDocument();
  });

  it('should not show error for valid email', () => {
    render(<RecipientInput {...defaultProps} value="valid@email.com" />);
    expect(screen.queryByText(getText('emailDrafting.validation.emailInvalid'))).not.toBeInTheDocument();
  });

  it('should not show error when email is empty', () => {
    render(<RecipientInput {...defaultProps} value="" />);
    expect(screen.queryByText(getText('emailDrafting.validation.emailRequired'))).not.toBeInTheDocument();
  });

  it('should show recent recipients on focus', async () => {
    const user = userEvent.setup();
    const recentRecipients = [
      {
        recipient: {
          id: '1',
          email: 'recent@example.com',
          name: 'Recent User',
          languagePreference: 'en' as const,
          previousInteractions: 5,
        },
        lastUsed: new Date(),
      },
    ];

    render(<RecipientInput {...defaultProps} recentRecipients={recentRecipients} />);

    await act(async () => {
      await user.click(screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')));
    });

    expect(await screen.findByText('Recent User')).toBeInTheDocument();
    expect(await screen.findByText('recent@example.com')).toBeInTheDocument();
  });

  it('should call onSelectRecent when clicking recent recipient', async () => {
    const user = userEvent.setup();
    const onSelectRecent = jest.fn();
    const recipient = {
      id: '1',
      email: 'recent@example.com',
      name: 'Recent',
      languagePreference: 'en' as const,
      previousInteractions: 1,
    };
    const recentRecipients = [{ recipient, lastUsed: new Date() }];

    render(
      <RecipientInput
        {...defaultProps}
        recentRecipients={recentRecipients}
        onSelectRecent={onSelectRecent}
      />
    );

    await act(async () => {
      await user.click(screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')));
    });
    const recentRecipient = await screen.findByText('Recent');
    await act(async () => {
      await user.click(recentRecipient);
    });

    expect(onSelectRecent).toHaveBeenCalledWith(recipient);
  });

  it('should have aria-invalid for invalid email', () => {
    render(<RecipientInput {...defaultProps} value="invalid" />);

    const emailInput = screen.getByLabelText(getText('emailDrafting.aria.recipientEmail'));
    expect(emailInput).toHaveAttribute('aria-invalid', 'true');
  });
});

// ============================================================================
// Key Points Editor Tests
// ============================================================================

describe('KeyPointsEditor', () => {
  it('should render input and add button', () => {
    render(<KeyPointsEditor points={[]} onChange={jest.fn()} />);

    expect(screen.getByLabelText(getText('emailDrafting.aria.addKeyPoint'))).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: getText('emailDrafting.actions.add') })
    ).toBeInTheDocument();
  });

  it('should add point when clicking Add button', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<KeyPointsEditor points={[]} onChange={onChange} />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.addKeyPoint')),
        'New point'
      );
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: getText('emailDrafting.actions.add') }));
    });

    expect(onChange).toHaveBeenCalledWith(['New point']);
  });

  it('should add point when pressing Enter', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<KeyPointsEditor points={[]} onChange={onChange} />);

    const input = screen.getByLabelText(getText('emailDrafting.aria.addKeyPoint'));
    await act(async () => {
      await user.type(input, 'Enter pressed{enter}');
    });

    expect(onChange).toHaveBeenCalledWith(['Enter pressed']);
  });

  it('should clear input after adding', async () => {
    const user = userEvent.setup();
    render(<KeyPointsEditor points={[]} onChange={jest.fn()} />);

    const input = screen.getByLabelText(getText('emailDrafting.aria.addKeyPoint'));
    await act(async () => {
      await user.type(input, 'Test point');
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: getText('emailDrafting.actions.add') }));
    });

    expect(input).toHaveValue('');
  });

  it('should display existing points', () => {
    render(<KeyPointsEditor points={['Point 1', 'Point 2']} onChange={jest.fn()} />);

    expect(screen.getByText('Point 1')).toBeInTheDocument();
    expect(screen.getByText('Point 2')).toBeInTheDocument();
  });

  it('should remove point when clicking remove button', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<KeyPointsEditor points={['Point 1', 'Point 2']} onChange={onChange} />);

    await act(async () => {
      await user.click(
        screen.getByLabelText(getText('emailDrafting.aria.removeKeyPoint', { point: 'Point 1' }))
      );
    });

    expect(onChange).toHaveBeenCalledWith(['Point 2']);
  });

  it('should not add empty points', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<KeyPointsEditor points={[]} onChange={onChange} />);

    await act(async () => {
      await user.click(screen.getByRole('button', { name: getText('emailDrafting.actions.add') }));
    });

    expect(onChange).not.toHaveBeenCalled();
  });

  it('should trim whitespace from points', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<KeyPointsEditor points={[]} onChange={onChange} />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.addKeyPoint')),
        '  Trimmed  '
      );
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: getText('emailDrafting.actions.add') }));
    });

    expect(onChange).toHaveBeenCalledWith(['Trimmed']);
  });

  it('should have list role for points', () => {
    render(<KeyPointsEditor points={['Point 1']} onChange={jest.fn()} />);
    expect(
      screen.getByRole('list', { name: getText('emailDrafting.aria.keyPointsList') })
    ).toBeInTheDocument();
  });
});

// ============================================================================
// Draft Preview Tests
// ============================================================================

describe('DraftPreview', () => {
  const mockDraft: GeneratedDraft = {
    id: 'draft-1',
    requestId: 'req-1',
    subject: 'Test Subject',
    bodyPlain: 'Dear John,\n\nTest body content.\n\nBest regards,\nSender',
    bodyHtml: '<p>Test</p>',
    salutation: 'Dear John,',
    opening: 'Test opening',
    mainContent: ['Point 1', 'Point 2'],
    closing: 'Best regards,',
    signature: 'Sender',
    status: 'ready' as DraftStatus,
    confidenceScore: 0.85,
    alternatives: [],
    complianceIssues: [],
    suggestions: [],
    tokensUsed: 100,
    generationTimeMs: 450,
    createdAt: new Date(),
    editsMade: [],
  };

  it('should render draft preview header', () => {
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);
    expect(screen.getByText(getText('emailDrafting.preview.title'))).toBeInTheDocument();
  });

  it('should display subject', () => {
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);
    expect(screen.getByText('Test Subject')).toBeInTheDocument();
  });

  it('should display body', () => {
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);
    expect(screen.getByText(/Test body content/)).toBeInTheDocument();
  });

  it('should display status badge', () => {
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);
    expect(screen.getByText(getText('emailDrafting.status.ready'))).toBeInTheDocument();
  });

  it('should display confidence score', () => {
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);
    expect(
      screen.getByText(
        getText('emailDrafting.preview.confidence', {
          score: formatConfidenceScore(mockDraft.confidenceScore),
        })
      )
    ).toBeInTheDocument();
  });

  it('should display generation time', () => {
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);
    const time = formatGenerationTime(mockDraft.generationTimeMs, {
      milliseconds: getText('emailDrafting.units.milliseconds'),
      seconds: getText('emailDrafting.units.seconds'),
    });
    expect(
      screen.getByText(
        getText('emailDrafting.preview.generatedIn', {
          time,
        })
      )
    ).toBeInTheDocument();
  });

  it('should call onCopy when copy button clicked', async () => {
    const user = userEvent.setup();
    const onCopy = jest.fn();
    render(<DraftPreview draft={mockDraft} onEdit={jest.fn()} onCopy={onCopy} />);

    await user.click(screen.getByLabelText(getText('emailDrafting.aria.copyToClipboard')));

    expect(onCopy).toHaveBeenCalled();
  });

  it('should call onEdit with subject when edit subject clicked', async () => {
    const user = userEvent.setup();
    const onEdit = jest.fn();
    render(<DraftPreview draft={mockDraft} onEdit={onEdit} onCopy={jest.fn()} />);

    await user.click(screen.getByLabelText(getText('emailDrafting.aria.editSubject')));

    expect(onEdit).toHaveBeenCalledWith('subject');
  });

  it('should call onEdit with body when edit button clicked', async () => {
    const user = userEvent.setup();
    const onEdit = jest.fn();
    render(<DraftPreview draft={mockDraft} onEdit={onEdit} onCopy={jest.fn()} />);

    await user.click(screen.getByText(getText('emailDrafting.actions.edit')));

    expect(onEdit).toHaveBeenCalledWith('body');
  });

  it('should show different status colors', () => {
    const approvedDraft = { ...mockDraft, status: 'approved' as DraftStatus };
    render(<DraftPreview draft={approvedDraft} onEdit={jest.fn()} onCopy={jest.fn()} />);

    expect(screen.getByText(getText('emailDrafting.status.approved'))).toBeInTheDocument();
  });
});

// ============================================================================
// Compliance Panel Tests
// ============================================================================

describe('CompliancePanel', () => {
  it('should show success message when no issues', () => {
    render(<CompliancePanel issues={[]} />);
    expect(screen.getByText(getText('emailDrafting.compliance.none'))).toBeInTheDocument();
  });

  it('should show issue count', () => {
    render(<CompliancePanel issues={['Issue 1', 'Issue 2']} />);
    expect(
      screen.getByText(getText('emailDrafting.compliance.title', { count: 2 }))
    ).toBeInTheDocument();
  });

  it('should list all issues', () => {
    render(<CompliancePanel issues={['First issue', 'Second issue']} />);

    expect(screen.getByText('First issue')).toBeInTheDocument();
    expect(screen.getByText('Second issue')).toBeInTheDocument();
  });

  it('should have warning styling when issues present', () => {
    const { container } = render(<CompliancePanel issues={['Issue']} />);
    expect(container.firstChild).toHaveClass('bg-rams-panel');
    expect(
      screen.getByText(getText('emailDrafting.compliance.title', { count: 1 })).parentElement
    ).toHaveClass('text-rams-orange');
  });

  it('should have success styling when no issues', () => {
    const { container } = render(<CompliancePanel issues={[]} />);
    expect(container.firstChild).toHaveClass('bg-rams-panel');
    expect(screen.getByText(getText('emailDrafting.compliance.none')).parentElement).toHaveClass(
      'text-rams-green'
    );
  });
});

// ============================================================================
// Suggestions Panel Tests
// ============================================================================

describe('SuggestionsPanel', () => {
  it('should return null when no suggestions', () => {
    const { container } = render(<SuggestionsPanel suggestions={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('should show suggestion count', () => {
    render(<SuggestionsPanel suggestions={['Suggestion 1']} />);
    expect(
      screen.getByText(getText('emailDrafting.suggestions.title', { count: 1 }))
    ).toBeInTheDocument();
  });

  it('should list all suggestions', () => {
    render(<SuggestionsPanel suggestions={['Add greeting', 'Shorten email']} />);

    expect(screen.getByText('Add greeting')).toBeInTheDocument();
    expect(screen.getByText('Shorten email')).toBeInTheDocument();
  });

  it('should show Apply button when onApply provided', () => {
    render(<SuggestionsPanel suggestions={['Suggestion']} onApply={jest.fn()} />);
    expect(screen.getByText(getText('emailDrafting.actions.apply'))).toBeInTheDocument();
  });

  it('should not show Apply button when onApply not provided', () => {
    render(<SuggestionsPanel suggestions={['Suggestion']} />);
    expect(screen.queryByText(getText('emailDrafting.actions.apply'))).not.toBeInTheDocument();
  });

  it('should call onApply when Apply clicked', async () => {
    const user = userEvent.setup();
    const onApply = jest.fn();
    render(<SuggestionsPanel suggestions={['Apply this']} onApply={onApply} />);

    await user.click(screen.getByText(getText('emailDrafting.actions.apply')));

    expect(onApply).toHaveBeenCalledWith('Apply this');
  });
});

// ============================================================================
// Alternative Subjects Tests
// ============================================================================

describe('AlternativeSubjects', () => {
  it('should return null when no alternatives', () => {
    const { container } = render(<AlternativeSubjects alternatives={[]} onSelect={jest.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('should display alternatives', () => {
    const alternatives = ['Alternative Subject: Option 1', 'Alternative Subject: Option 2'];
    render(<AlternativeSubjects alternatives={alternatives} onSelect={jest.fn()} />);

    expect(screen.getByText('Option 1')).toBeInTheDocument();
    expect(screen.getByText('Option 2')).toBeInTheDocument();
  });

  it('should strip prefix from display', () => {
    render(
      <AlternativeSubjects
        alternatives={['Alternative Subject: Clean Title']}
        onSelect={jest.fn()}
      />
    );

    expect(screen.getByText('Clean Title')).toBeInTheDocument();
    expect(screen.queryByText('Alternative Subject:')).not.toBeInTheDocument();
  });

  it('should call onSelect when alternative clicked', async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    render(
      <AlternativeSubjects
        alternatives={['Alternative Subject: Selected One']}
        onSelect={onSelect}
      />
    );

    await user.click(screen.getByText('Selected One'));

    expect(onSelect).toHaveBeenCalledWith('Selected One');
  });

  it('should show label', () => {
    render(
      <AlternativeSubjects alternatives={['Alternative Subject: Test']} onSelect={jest.fn()} />
    );
    expect(screen.getByText(getText('emailDrafting.alternatives.title'))).toBeInTheDocument();
  });
});

// ============================================================================
// Draft List Item Tests
// ============================================================================

describe('DraftListItem', () => {
  const mockDraft: GeneratedDraft = {
    id: 'draft-1',
    requestId: 'req-1',
    subject: 'Test Email Subject',
    bodyPlain: 'This is the body of the email which should be truncated...',
    bodyHtml: '<p>Test</p>',
    salutation: 'Hi',
    opening: 'Opening',
    mainContent: [],
    closing: 'Regards',
    signature: 'Sender',
    status: 'ready' as DraftStatus,
    confidenceScore: 0.9,
    alternatives: [],
    complianceIssues: [],
    suggestions: [],
    tokensUsed: 100,
    generationTimeMs: 200,
    createdAt: new Date('2024-01-15T10:00:00'),
    editsMade: [],
  };

  it('should render subject', () => {
    render(<DraftListItem draft={mockDraft} isActive={false} onClick={jest.fn()} />);
    expect(screen.getByText('Test Email Subject')).toBeInTheDocument();
  });

  it('should render truncated body preview', () => {
    render(<DraftListItem draft={mockDraft} isActive={false} onClick={jest.fn()} />);
    expect(screen.getByText(/This is the body/)).toBeInTheDocument();
  });

  it('should render status badge', () => {
    render(<DraftListItem draft={mockDraft} isActive={false} onClick={jest.fn()} />);
    expect(screen.getByText(getText('emailDrafting.status.ready'))).toBeInTheDocument();
  });

  it('should have active styling when active', () => {
    render(<DraftListItem draft={mockDraft} isActive={true} onClick={jest.fn()} />);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('border-rams-steel', 'bg-rams-panel');
  });

  it('should not have active styling when inactive', () => {
    render(<DraftListItem draft={mockDraft} isActive={false} onClick={jest.fn()} />);
    const button = screen.getByRole('button');
    expect(button).not.toHaveClass('border-rams-steel');
  });

  it('should call onClick when clicked', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    render(<DraftListItem draft={mockDraft} isActive={false} onClick={onClick} />);

    await user.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalled();
  });
});

// ============================================================================
// Drafts List Tests
// ============================================================================

describe('DraftsList', () => {
  it('should show empty state when no drafts', () => {
    render(<DraftsList />);
    expect(screen.getByText(getText('emailDrafting.empty.list'))).toBeInTheDocument();
  });

  it('should render drafts when present', async () => {
    const store = useEmailDraftingStore.getState();
    const request = {
      id: 'req-1',
      context: {
        purpose: 'custom' as const,
        recipient: {
          id: '1',
          email: 'test@example.com',
          languagePreference: 'en' as const,
          previousInteractions: 0,
        },
        keyPoints: [],
        attachments: [],
        tone: 'professional' as const,
        language: 'en' as const,
        includeSignature: true,
        maxParagraphs: 4,
      },
      senderName: 'Test',
      senderEmail: 'test@co.com',
      companyName: 'Co',
      requestedAt: new Date(),
    };

    await store.generateDraft(request);

    render(<DraftsList />);

    expect(
      screen.getByRole('list', { name: getText('emailDrafting.aria.draftsList') })
    ).toBeInTheDocument();
  });

  it('should highlight active draft', async () => {
    const store = useEmailDraftingStore.getState();
    const request = {
      id: 'req-1',
      context: {
        purpose: 'quote_followup' as const,
        recipient: {
          id: '1',
          email: 'test@example.com',
          languagePreference: 'en' as const,
          previousInteractions: 0,
        },
        keyPoints: [],
        attachments: [],
        referenceNumber: 'Q-123',
        tone: 'professional' as const,
        language: 'en' as const,
        includeSignature: true,
        maxParagraphs: 4,
      },
      senderName: 'Test',
      senderEmail: 'test@co.com',
      companyName: 'Co',
      requestedAt: new Date(),
    };

    const draft = await store.generateDraft(request);

    render(<DraftsList />);

    // The active draft should have RAMS border
    const listItem = screen.getByRole('button');
    expect(listItem).toHaveClass('border-rams-steel');
  });
});

// ============================================================================
// Email Composer Integration Tests
// ============================================================================

describe('EmailComposer', () => {
  it('should render header', () => {
    render(<EmailComposer />);
    expect(screen.getByText(getText('emailDrafting.title'))).toBeInTheDocument();
  });

  it('should render recipient input', () => {
    render(<EmailComposer />);
    expect(screen.getByLabelText(getText('emailDrafting.aria.recipientEmail'))).toBeInTheDocument();
  });

  it('should render purpose selector', () => {
    render(<EmailComposer />);
    expect(screen.getByText(getText('emailDrafting.placeholders.selectPurpose'))).toBeInTheDocument();
  });

  it('should render tone selector', () => {
    render(<EmailComposer />);
    expect(screen.getByText(getText('emailDrafting.tone.professional'))).toBeInTheDocument();
    expect(screen.getByText(getText('emailDrafting.tone.formal'))).toBeInTheDocument();
  });

  it('should render language selector', () => {
    render(<EmailComposer />);
    expect(screen.getByLabelText(getText('emailDrafting.aria.selectLanguage'))).toBeInTheDocument();
  });

  it('should render key points editor', () => {
    render(<EmailComposer />);
    expect(screen.getByLabelText(getText('emailDrafting.aria.addKeyPoint'))).toBeInTheDocument();
  });

  it('should render generate button', () => {
    render(<EmailComposer />);
    expect(screen.getByText(getText('emailDrafting.actions.generateDraft'))).toBeInTheDocument();
  });

  it('should disable generate button initially', () => {
    render(<EmailComposer />);
    expect(screen.getByText(getText('emailDrafting.actions.generateDraft'))).toBeDisabled();
  });

  it('should enable generate button when form is valid', async () => {
    const user = userEvent.setup();
    render(<EmailComposer />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'test@example.com'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.placeholders.selectPurpose')));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });

    await act(async () => {
      await user.selectOptions(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityType')),
        'rfq'
      );
      await user.type(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityId')),
        'RFQ-2024-001'
      );
    });

    expect(screen.getByText(getText('emailDrafting.actions.generateDraft'))).not.toBeDisabled();
  });

  it('should show empty state for preview initially', () => {
    render(<EmailComposer />);
    expect(screen.getByText(getText('emailDrafting.empty.title'))).toBeInTheDocument();
  });

  it('should call onClose when close button clicked', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    render(<EmailComposer onClose={onClose} />);

    await user.click(screen.getByLabelText(getText('emailDrafting.aria.close')));

    expect(onClose).toHaveBeenCalled();
  });

  it('should not show close button when onClose not provided', () => {
    render(<EmailComposer />);
    expect(screen.queryByLabelText(getText('emailDrafting.aria.close'))).not.toBeInTheDocument();
  });

  it('should use initial recipient when provided', () => {
    const recipient = {
      id: '1',
      email: 'initial@example.com',
      name: 'Initial User',
      languagePreference: 'en' as const,
      previousInteractions: 0,
    };

    render(<EmailComposer initialRecipient={recipient} />);

    expect(screen.getByLabelText(getText('emailDrafting.aria.recipientEmail'))).toHaveValue(
      'initial@example.com'
    );
    expect(screen.getByLabelText(getText('emailDrafting.aria.recipientName'))).toHaveValue(
      'Initial User'
    );
  });

  it('should use initial purpose when provided', () => {
    render(<EmailComposer initialPurpose="meeting_request" />);
    expect(screen.getByText(getText('emailDrafting.purpose.meetingRequest'))).toBeInTheDocument();
  });

  it('should use reference number when provided', () => {
    render(<EmailComposer referenceNumber="RFQ-2024-001" />);

    const refInput = screen.getByPlaceholderText(getText('emailDrafting.placeholders.referenceNumber'));
    expect(refInput).toHaveValue('RFQ-2024-001');
  });

  it('should generate draft when form submitted', async () => {
    const user = userEvent.setup();
    render(<EmailComposer />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'john@example.com'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.placeholders.selectPurpose')));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });

    await act(async () => {
      await user.selectOptions(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityType')),
        'rfq'
      );
      await user.type(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityId')),
        'RFQ-2024-001'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.actions.generateDraft')));
      await flushPromises();
    });

    await waitFor(() => {
      expect(screen.getByText(getText('emailDrafting.preview.title'))).toBeInTheDocument();
    });
  });

  it('should show draft after generation', async () => {
    const user = userEvent.setup();
    render(<EmailComposer />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'john@example.com'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.placeholders.selectPurpose')));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });
    await act(async () => {
      await user.selectOptions(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityType')),
        'rfq'
      );
      await user.type(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityId')),
        'RFQ-2024-001'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.actions.generateDraft')));
      await flushPromises();
    });

    await waitFor(() => {
      expect(screen.queryByText(getText('emailDrafting.empty.title'))).not.toBeInTheDocument();
    });
  });

  it('should show regenerate button after draft generated', async () => {
    const user = userEvent.setup();
    render(<EmailComposer />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'john@example.com'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.placeholders.selectPurpose')));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });
    await act(async () => {
      await user.selectOptions(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityType')),
        'rfq'
      );
      await user.type(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityId')),
        'RFQ-2024-001'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.actions.generateDraft')));
      await flushPromises();
    });

    await waitFor(() => {
      expect(screen.getByText(getText('emailDrafting.actions.regenerate'))).toBeInTheDocument();
    });
  });

  it('should show send button after draft generated', async () => {
    const user = userEvent.setup();
    render(<EmailComposer />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'john@example.com'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.placeholders.selectPurpose')));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });
    await act(async () => {
      await user.selectOptions(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityType')),
        'rfq'
      );
      await user.type(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityId')),
        'RFQ-2024-001'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.actions.generateDraft')));
      await flushPromises();
    });

    await waitFor(() => {
      expect(screen.getByText(getText('emailDrafting.actions.send'))).toBeInTheDocument();
    });
  });

  it('should copy draft to clipboard', async () => {
    const user = userEvent.setup();
    
    // Mock clipboard using defineProperty
    const writeTextMock = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      writable: true,
      configurable: true,
    });

    render(<EmailComposer />);

    await act(async () => {
      await user.type(
        screen.getByLabelText(getText('emailDrafting.aria.recipientEmail')),
        'john@example.com'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.placeholders.selectPurpose')));
    });
    const quoteFollowupOption = await screen.findByText(
      getText('emailDrafting.purpose.quoteFollowup')
    );
    await act(async () => {
      await user.click(quoteFollowupOption);
    });
    await act(async () => {
      await user.selectOptions(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityType')),
        'rfq'
      );
      await user.type(
        screen.getByLabelText(getText('emailDrafting.fields.threadEntityId')),
        'RFQ-2024-001'
      );
    });
    await act(async () => {
      await user.click(screen.getByText(getText('emailDrafting.actions.generateDraft')));
      await flushPromises();
    });

    await waitFor(() => {
      expect(
        screen.getByLabelText(getText('emailDrafting.aria.copyToClipboard'))
      ).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByLabelText(getText('emailDrafting.aria.copyToClipboard')));
      await flushPromises();
    });

    await waitFor(() => {
      expect(screen.getByText(getText('emailDrafting.notifications.copied'))).toBeInTheDocument();
    });
  });
});
