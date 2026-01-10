/**
 * Tests for Security, Privacy & Compliance UI/UX Components
 * 
 * Section 19.12: Security, Privacy & Compliance UI/UX
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  PERMISSION,
  ROLE,
  ROLE_PERMISSIONS,
  CONFIDENTIALITY,
  SYNC_STATUS,
  AUDIT_ACTION,
  RBACProvider,
  useRBAC,
  PermissionGate,
  MaskedData,
  PrivacyIndicator,
  SenseiProcessing,
  ConfidentialityLabel,
  DataClassificationBanner,
  AuditTrail,
  ChangeHistoryModal,
  SecureActionButton,
  SessionSecurity,
  User,
  AuditEntry,
} from '../security-privacy';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Security Privacy Constants', () => {
  describe('PERMISSION', () => {
    it('should define all permissions', () => {
      expect(PERMISSION.READ).toBe('read');
      expect(PERMISSION.WRITE).toBe('write');
      expect(PERMISSION.DELETE).toBe('delete');
      expect(PERMISSION.ADMIN).toBe('admin');
      expect(PERMISSION.MANAGE_USERS).toBe('manage_users');
      expect(PERMISSION.VIEW_FINANCIALS).toBe('view_financials');
      expect(PERMISSION.VIEW_CONFIDENTIAL).toBe('view_confidential');
      expect(PERMISSION.EXPORT_DATA).toBe('export_data');
    });
  });

  describe('ROLE', () => {
    it('should define all roles', () => {
      expect(ROLE.GUEST).toBe('guest');
      expect(ROLE.VIEWER).toBe('viewer');
      expect(ROLE.OPERATOR).toBe('operator');
      expect(ROLE.SUPERVISOR).toBe('supervisor');
      expect(ROLE.MANAGER).toBe('manager');
      expect(ROLE.ADMIN).toBe('admin');
      expect(ROLE.OWNER).toBe('owner');
    });
  });

  describe('ROLE_PERMISSIONS', () => {
    it('should map roles to permissions', () => {
      expect(ROLE_PERMISSIONS[ROLE.GUEST]).toContain(PERMISSION.READ);
      expect(ROLE_PERMISSIONS[ROLE.ADMIN]).toContain(PERMISSION.ADMIN);
      expect(ROLE_PERMISSIONS[ROLE.OWNER]).toContain(PERMISSION.VIEW_CONFIDENTIAL);
    });

    it('should give admin more permissions than viewer', () => {
      expect(ROLE_PERMISSIONS[ROLE.ADMIN].length).toBeGreaterThan(ROLE_PERMISSIONS[ROLE.VIEWER].length);
    });
  });

  describe('CONFIDENTIALITY', () => {
    it('should define all levels', () => {
      expect(CONFIDENTIALITY.PUBLIC).toBe('public');
      expect(CONFIDENTIALITY.INTERNAL).toBe('internal');
      expect(CONFIDENTIALITY.CONFIDENTIAL).toBe('confidential');
      expect(CONFIDENTIALITY.RESTRICTED).toBe('restricted');
    });
  });

  describe('SYNC_STATUS', () => {
    it('should define all statuses', () => {
      expect(SYNC_STATUS.IDLE).toBe('idle');
      expect(SYNC_STATUS.SYNCING).toBe('syncing');
      expect(SYNC_STATUS.PROCESSING).toBe('processing');
      expect(SYNC_STATUS.COMPLETE).toBe('complete');
      expect(SYNC_STATUS.ERROR).toBe('error');
    });
  });

  describe('AUDIT_ACTION', () => {
    it('should define all actions', () => {
      expect(AUDIT_ACTION.CREATE).toBe('create');
      expect(AUDIT_ACTION.UPDATE).toBe('update');
      expect(AUDIT_ACTION.DELETE).toBe('delete');
      expect(AUDIT_ACTION.VIEW).toBe('view');
      expect(AUDIT_ACTION.EXPORT).toBe('export');
      expect(AUDIT_ACTION.SHARE).toBe('share');
      expect(AUDIT_ACTION.PERMISSION_CHANGE).toBe('permission_change');
    });
  });
});

// =============================================================================
// RBAC PROVIDER TESTS
// =============================================================================

describe('RBACProvider', () => {
  const mockAdmin: User = {
    id: '1',
    name: 'Admin User',
    email: 'admin@example.com',
    role: ROLE.ADMIN,
  };

  function RBACTester() {
    const { user, hasPermission, hasRole, hasMinimumRole, setUser } = useRBAC();
    return (
      <div>
        <span data-testid="user">{user?.name || 'none'}</span>
        <span data-testid="has-read">{hasPermission(PERMISSION.READ).toString()}</span>
        <span data-testid="has-admin">{hasPermission(PERMISSION.ADMIN).toString()}</span>
        <span data-testid="is-admin">{hasRole(ROLE.ADMIN).toString()}</span>
        <span data-testid="min-supervisor">{hasMinimumRole(ROLE.SUPERVISOR).toString()}</span>
        <button onClick={() => setUser(mockAdmin)}>Set Admin</button>
        <button onClick={() => setUser(null)}>Clear User</button>
      </div>
    );
  }

  it('should start with no user', () => {
    render(
      <RBACProvider>
        <RBACTester />
      </RBACProvider>
    );

    expect(screen.getByTestId('user')).toHaveTextContent('none');
  });

  it('should accept initial user', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <RBACTester />
      </RBACProvider>
    );

    expect(screen.getByTestId('user')).toHaveTextContent('Admin User');
  });

  it('should set user permissions based on role', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <RBACTester />
      </RBACProvider>
    );

    expect(screen.getByTestId('has-read')).toHaveTextContent('true');
    expect(screen.getByTestId('has-admin')).toHaveTextContent('true');
  });

  it('should check role correctly', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <RBACTester />
      </RBACProvider>
    );

    expect(screen.getByTestId('is-admin')).toHaveTextContent('true');
  });

  it('should check minimum role correctly', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <RBACTester />
      </RBACProvider>
    );

    expect(screen.getByTestId('min-supervisor')).toHaveTextContent('true');
  });

  it('should update user', async () => {
    const user = userEvent.setup();

    render(
      <RBACProvider>
        <RBACTester />
      </RBACProvider>
    );

    await user.click(screen.getByText('Set Admin'));
    expect(screen.getByTestId('user')).toHaveTextContent('Admin User');
  });

  it('should throw error when useRBAC is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<RBACTester />)).toThrow('useRBAC must be used within RBACProvider');
    consoleError.mockRestore();
  });
});

// =============================================================================
// PERMISSION GATE TESTS
// =============================================================================

describe('PermissionGate', () => {
  const mockAdmin: User = {
    id: '1',
    name: 'Admin',
    email: 'admin@example.com',
    role: ROLE.ADMIN,
  };

  const mockViewer: User = {
    id: '2',
    name: 'Viewer',
    email: 'viewer@example.com',
    role: ROLE.VIEWER,
  };

  it('should render children when user has permission', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <PermissionGate require={PERMISSION.ADMIN}>
          <span>Secret Content</span>
        </PermissionGate>
      </RBACProvider>
    );

    expect(screen.getByText('Secret Content')).toBeInTheDocument();
  });

  it('should not render children when user lacks permission', () => {
    render(
      <RBACProvider initialUser={mockViewer}>
        <PermissionGate require={PERMISSION.ADMIN}>
          <span>Secret Content</span>
        </PermissionGate>
      </RBACProvider>
    );

    expect(screen.queryByText('Secret Content')).not.toBeInTheDocument();
  });

  it('should render fallback when user lacks permission', () => {
    render(
      <RBACProvider initialUser={mockViewer}>
        <PermissionGate require={PERMISSION.ADMIN} fallback={<span>Access Denied</span>}>
          <span>Secret Content</span>
        </PermissionGate>
      </RBACProvider>
    );

    expect(screen.getByText('Access Denied')).toBeInTheDocument();
  });

  it('should check multiple permissions with requireAll=false', () => {
    render(
      <RBACProvider initialUser={mockViewer}>
        <PermissionGate require={[PERMISSION.READ, PERMISSION.ADMIN]} requireAll={false}>
          <span>Content</span>
        </PermissionGate>
      </RBACProvider>
    );

    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('should check multiple permissions with requireAll=true', () => {
    render(
      <RBACProvider initialUser={mockViewer}>
        <PermissionGate require={[PERMISSION.READ, PERMISSION.ADMIN]} requireAll={true}>
          <span>Content</span>
        </PermissionGate>
      </RBACProvider>
    );

    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('should check minimum role', () => {
    render(
      <RBACProvider initialUser={mockViewer}>
        <PermissionGate requireMinimumRole={ROLE.MANAGER}>
          <span>Manager Content</span>
        </PermissionGate>
      </RBACProvider>
    );

    expect(screen.queryByText('Manager Content')).not.toBeInTheDocument();
  });
});

// =============================================================================
// MASKED DATA TESTS
// =============================================================================

describe('MaskedData', () => {
  const mockAdmin: User = {
    id: '1',
    name: 'Admin',
    email: 'admin@example.com',
    role: ROLE.ADMIN,
  };

  it('should mask value by default', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <MaskedData value="$125,000.00" />
      </RBACProvider>
    );

    expect(screen.queryByText('$125,000.00')).not.toBeInTheDocument();
  });

  it('should reveal value when toggle clicked', async () => {
    const user = userEvent.setup();

    render(
      <RBACProvider initialUser={mockAdmin}>
        <MaskedData value="$125,000.00" />
      </RBACProvider>
    );

    await user.click(screen.getByLabelText('Reveal sensitive data'));
    expect(screen.getByText('$125,000.00')).toBeInTheDocument();
  });

  it('should show lock icon when user lacks permission', () => {
    const mockViewer: User = {
      id: '2',
      name: 'Viewer',
      email: 'viewer@example.com',
      role: ROLE.VIEWER,
    };

    render(
      <RBACProvider initialUser={mockViewer}>
        <MaskedData value="$125,000.00" requirePermission={PERMISSION.VIEW_FINANCIALS} />
      </RBACProvider>
    );

    expect(screen.getByText('🔒')).toBeInTheDocument();
  });

  it('should render label when provided', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <MaskedData value="secret" label="Password" />
      </RBACProvider>
    );

    expect(screen.getByText('Password:')).toBeInTheDocument();
  });
});

// =============================================================================
// PRIVACY INDICATOR TESTS
// =============================================================================

describe('PrivacyIndicator', () => {
  it('should show idle status', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.IDLE} />);
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });

  it('should show syncing status', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.SYNCING} />);
    expect(screen.getByText('Syncing...')).toBeInTheDocument();
  });

  it('should show processing status', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.PROCESSING} />);
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('should show complete status', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.COMPLETE} />);
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('should show error status', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.ERROR} />);
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('should show custom label', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.SYNCING} label="Uploading..." />);
    expect(screen.getByText('Uploading...')).toBeInTheDocument();
  });

  it('should hide label when showLabel=false', () => {
    render(<PrivacyIndicator status={SYNC_STATUS.SYNCING} showLabel={false} />);
    expect(screen.queryByText('Syncing...')).not.toBeInTheDocument();
  });
});

// =============================================================================
// SENSEI PROCESSING TESTS
// =============================================================================

describe('SenseiProcessing', () => {
  it('should not render when not processing', () => {
    render(<SenseiProcessing isProcessing={false} />);
    expect(screen.queryByTestId('sensei-processing')).not.toBeInTheDocument();
  });

  it('should render when processing', () => {
    render(<SenseiProcessing isProcessing={true} />);
    expect(screen.getByTestId('sensei-processing')).toBeInTheDocument();
  });

  it('should show model name', () => {
    render(<SenseiProcessing isProcessing={true} modelName="Quote Optimizer" />);
    expect(screen.getByText('Quote Optimizer is analyzing...')).toBeInTheDocument();
  });

  it('should show progress bar when progress provided', () => {
    render(<SenseiProcessing isProcessing={true} progress={45} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('should show local processing message', () => {
    render(<SenseiProcessing isProcessing={true} />);
    expect(screen.getByText(/local processing/i)).toBeInTheDocument();
  });
});

// =============================================================================
// CONFIDENTIALITY LABEL TESTS
// =============================================================================

describe('ConfidentialityLabel', () => {
  it('should render public label', () => {
    render(<ConfidentialityLabel level={CONFIDENTIALITY.PUBLIC} />);
    expect(screen.getByText('Public')).toBeInTheDocument();
  });

  it('should render internal label', () => {
    render(<ConfidentialityLabel level={CONFIDENTIALITY.INTERNAL} />);
    expect(screen.getByText('Internal')).toBeInTheDocument();
  });

  it('should render confidential label', () => {
    render(<ConfidentialityLabel level={CONFIDENTIALITY.CONFIDENTIAL} />);
    expect(screen.getByText('Confidential')).toBeInTheDocument();
  });

  it('should render restricted label', () => {
    render(<ConfidentialityLabel level={CONFIDENTIALITY.RESTRICTED} />);
    expect(screen.getByText('Restricted')).toBeInTheDocument();
  });

  it('should show icon by default', () => {
    render(<ConfidentialityLabel level={CONFIDENTIALITY.CONFIDENTIAL} />);
    expect(screen.getByText('🔐')).toBeInTheDocument();
  });

  it('should hide icon when showIcon=false', () => {
    render(<ConfidentialityLabel level={CONFIDENTIALITY.CONFIDENTIAL} showIcon={false} />);
    expect(screen.queryByText('🔐')).not.toBeInTheDocument();
  });
});

// =============================================================================
// DATA CLASSIFICATION BANNER TESTS
// =============================================================================

describe('DataClassificationBanner', () => {
  it('should render with level', () => {
    render(<DataClassificationBanner level={CONFIDENTIALITY.CONFIDENTIAL} />);
    expect(screen.getByTestId('classification-banner')).toBeInTheDocument();
    expect(screen.getByText('Confidential:')).toBeInTheDocument();
  });

  it('should show default message', () => {
    render(<DataClassificationBanner level={CONFIDENTIALITY.INTERNAL} />);
    expect(screen.getByText(/internal use only/i)).toBeInTheDocument();
  });

  it('should show custom message', () => {
    render(<DataClassificationBanner level={CONFIDENTIALITY.RESTRICTED} message="Handle with extreme care" />);
    expect(screen.getByText('Handle with extreme care')).toBeInTheDocument();
  });

  it('should be dismissible when dismissible=true', async () => {
    const user = userEvent.setup();

    render(<DataClassificationBanner level={CONFIDENTIALITY.PUBLIC} dismissible={true} />);

    expect(screen.getByTestId('classification-banner')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Dismiss banner'));
    expect(screen.queryByTestId('classification-banner')).not.toBeInTheDocument();
  });
});

// =============================================================================
// AUDIT TRAIL TESTS
// =============================================================================

describe('AuditTrail', () => {
  const mockEntries: AuditEntry[] = [
    {
      id: '1',
      timestamp: new Date(),
      action: AUDIT_ACTION.CREATE,
      userId: 'user1',
      userName: 'John Doe',
      entityType: 'Quote',
      entityId: 'q123',
      description: 'Created new quote',
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 3600000),
      action: AUDIT_ACTION.UPDATE,
      userId: 'user2',
      userName: 'Jane Smith',
      entityType: 'Quote',
      entityId: 'q123',
      description: 'Updated pricing',
      changes: [
        { field: 'price', oldValue: 100, newValue: 150 },
      ],
    },
  ];

  it('should render title', () => {
    render(<AuditTrail entries={mockEntries} title="Quote History" />);
    expect(screen.getByText('Quote History')).toBeInTheDocument();
  });

  it('should render entries', () => {
    render(<AuditTrail entries={mockEntries} />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('should show action type', () => {
    render(<AuditTrail entries={mockEntries} />);
    expect(screen.getByText('created')).toBeInTheDocument();
    expect(screen.getByText('updated')).toBeInTheDocument();
  });

  it('should show empty message when no entries', () => {
    render(<AuditTrail entries={[]} />);
    expect(screen.getByText(/no history entries/i)).toBeInTheDocument();
  });

  it('should filter by action type', async () => {
    const user = userEvent.setup();

    render(<AuditTrail entries={mockEntries} showFilters={true} />);

    await user.selectOptions(screen.getByLabelText('Filter by action type'), 'create');

    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
  });

  it('should expand changes when clicked', async () => {
    const user = userEvent.setup();

    render(<AuditTrail entries={mockEntries} />);

    await user.click(screen.getByText('Show 1 change(s)'));
    expect(screen.getByText('price:')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('should show load more button when hasMore', () => {
    const onLoadMore = jest.fn();

    render(<AuditTrail entries={mockEntries} hasMore={true} onLoadMore={onLoadMore} />);

    expect(screen.getByText('Load more history')).toBeInTheDocument();
  });
});

// =============================================================================
// CHANGE HISTORY MODAL TESTS
// =============================================================================

describe('ChangeHistoryModal', () => {
  const mockEntries: AuditEntry[] = [
    {
      id: '1',
      timestamp: new Date(),
      action: AUDIT_ACTION.CREATE,
      userId: 'user1',
      userName: 'John Doe',
      entityType: 'Quote',
      entityId: 'q123',
      description: 'Created new quote',
    },
  ];

  it('should not render when closed', () => {
    render(
      <ChangeHistoryModal
        isOpen={false}
        onClose={() => {}}
        entityType="Quote"
        entityId="q123"
        entries={mockEntries}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    render(
      <ChangeHistoryModal
        isOpen={true}
        onClose={() => {}}
        entityType="Quote"
        entityId="q123"
        entries={mockEntries}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should show entity info', () => {
    render(
      <ChangeHistoryModal
        isOpen={true}
        onClose={() => {}}
        entityType="Quote"
        entityId="q123"
        entityName="Q-2024-001"
        entries={mockEntries}
      />
    );

    // Check for the modal title
    expect(screen.getByText('Change History')).toBeInTheDocument();
    // Check for entity info in the subtitle (text split across elements)
    expect(screen.getByText((content, element) => {
      return element?.tagName === 'P' && content.includes('Q-2024-001');
    })).toBeInTheDocument();
  });

  it('should call onClose when close button clicked', async () => {
    const onClose = jest.fn();
    const user = userEvent.setup();

    render(
      <ChangeHistoryModal
        isOpen={true}
        onClose={onClose}
        entityType="Quote"
        entityId="q123"
        entries={mockEntries}
      />
    );

    await user.click(screen.getByLabelText('Close modal'));
    expect(onClose).toHaveBeenCalled();
  });
});

// =============================================================================
// SECURE ACTION BUTTON TESTS
// =============================================================================

describe('SecureActionButton', () => {
  const mockAdmin: User = {
    id: '1',
    name: 'Admin',
    email: 'admin@example.com',
    role: ROLE.ADMIN,
  };

  const mockViewer: User = {
    id: '2',
    name: 'Viewer',
    email: 'viewer@example.com',
    role: ROLE.VIEWER,
  };

  it('should render button', () => {
    render(
      <RBACProvider initialUser={mockAdmin}>
        <SecureActionButton onClick={() => {}}>Delete</SecureActionButton>
      </RBACProvider>
    );

    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('should call onClick when clicked', async () => {
    const onClick = jest.fn();
    const user = userEvent.setup();

    render(
      <RBACProvider initialUser={mockAdmin}>
        <SecureActionButton onClick={onClick}>Action</SecureActionButton>
      </RBACProvider>
    );

    await user.click(screen.getByText('Action'));
    expect(onClick).toHaveBeenCalled();
  });

  it('should be disabled when user lacks permission', () => {
    render(
      <RBACProvider initialUser={mockViewer}>
        <SecureActionButton onClick={() => {}} requirePermission={PERMISSION.DELETE}>
          Delete
        </SecureActionButton>
      </RBACProvider>
    );

    expect(screen.getByText('Delete')).toBeDisabled();
  });

  it('should show confirmation dialog when requireConfirmation', async () => {
    const user = userEvent.setup();

    render(
      <RBACProvider initialUser={mockAdmin}>
        <SecureActionButton
          onClick={() => {}}
          requireConfirmation={true}
          confirmationMessage="Are you sure?"
        >
          Delete
        </SecureActionButton>
      </RBACProvider>
    );

    await user.click(screen.getByText('Delete'));
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
  });

  it('should call onClick after confirmation', async () => {
    const onClick = jest.fn();
    const user = userEvent.setup();

    render(
      <RBACProvider initialUser={mockAdmin}>
        <SecureActionButton onClick={onClick} requireConfirmation={true}>
          Delete
        </SecureActionButton>
      </RBACProvider>
    );

    await user.click(screen.getByText('Delete'));
    await user.click(screen.getByText('Confirm'));
    expect(onClick).toHaveBeenCalled();
  });

  it('should close dialog on cancel', async () => {
    const user = userEvent.setup();

    render(
      <RBACProvider initialUser={mockAdmin}>
        <SecureActionButton onClick={() => {}} requireConfirmation={true}>
          Delete
        </SecureActionButton>
      </RBACProvider>
    );

    await user.click(screen.getByText('Delete'));
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    
    await user.click(screen.getByText('Cancel'));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});

// =============================================================================
// SESSION SECURITY TESTS
// =============================================================================

describe('SessionSecurity', () => {
  it('should show secure status', () => {
    render(<SessionSecurity isSecure={true} />);
    expect(screen.getByText('Secure session')).toBeInTheDocument();
    expect(screen.getByText('🔒')).toBeInTheDocument();
  });

  it('should show insecure status', () => {
    render(<SessionSecurity isSecure={false} />);
    expect(screen.getByText('Insecure connection')).toBeInTheDocument();
    expect(screen.getByText('⚠️')).toBeInTheDocument();
  });

  it('should show time remaining', () => {
    const expiry = new Date(Date.now() + 30 * 60000);
    render(<SessionSecurity isSecure={true} sessionExpiry={expiry} />);
    expect(screen.getByText(/remaining/i)).toBeInTheDocument();
  });

  it('should show extend button when onExtendSession provided', () => {
    const expiry = new Date(Date.now() + 30 * 60000);
    render(<SessionSecurity isSecure={true} sessionExpiry={expiry} onExtendSession={() => {}} />);
    expect(screen.getByText('Extend')).toBeInTheDocument();
  });

  it('should call onExtendSession when extend clicked', async () => {
    const onExtend = jest.fn();
    const user = userEvent.setup();
    const expiry = new Date(Date.now() + 30 * 60000);

    render(<SessionSecurity isSecure={true} sessionExpiry={expiry} onExtendSession={onExtend} />);

    await user.click(screen.getByText('Extend'));
    expect(onExtend).toHaveBeenCalled();
  });
});
