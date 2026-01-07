import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Avatar } from '../avatar';

describe('Avatar', () => {
  it('should render with fallback initials when no src', () => {
    render(<Avatar fallback="John Doe" />);
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('should use alt for initials if no fallback', () => {
    render(<Avatar alt="Jane Smith" />);
    expect(screen.getByText('JS')).toBeInTheDocument();
  });

  it('should show question mark if no fallback or alt', () => {
    render(<Avatar />);
    expect(screen.getByText('?')).toBeInTheDocument();
  });

  it('should render an image when src is provided', () => {
    render(<Avatar src="https://example.com/avatar.jpg" alt="User" />);
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://example.com/avatar.jpg');
  });

  it('should set alt attribute on image', () => {
    render(<Avatar src="https://example.com/avatar.jpg" alt="User Avatar" />);
    expect(screen.getByRole('img')).toHaveAttribute('alt', 'User Avatar');
  });

  it('should apply default size classes', () => {
    render(<Avatar data-testid="avatar" fallback="Test" />);
    const avatar = screen.getByTestId('avatar');
    
    expect(avatar).toHaveClass('h-10');
    expect(avatar).toHaveClass('w-10');
  });

  it('should apply xs size classes', () => {
    render(<Avatar size="xs" data-testid="avatar" fallback="Test" />);
    const avatar = screen.getByTestId('avatar');
    
    expect(avatar).toHaveClass('h-6');
    expect(avatar).toHaveClass('w-6');
  });

  it('should apply sm size classes', () => {
    render(<Avatar size="sm" data-testid="avatar" fallback="Test" />);
    const avatar = screen.getByTestId('avatar');
    
    expect(avatar).toHaveClass('h-8');
    expect(avatar).toHaveClass('w-8');
  });

  it('should apply lg size classes', () => {
    render(<Avatar size="lg" data-testid="avatar" fallback="Test" />);
    const avatar = screen.getByTestId('avatar');
    
    expect(avatar).toHaveClass('h-12');
    expect(avatar).toHaveClass('w-12');
  });

  it('should apply xl size classes', () => {
    render(<Avatar size="xl" data-testid="avatar" fallback="Test" />);
    const avatar = screen.getByTestId('avatar');
    
    expect(avatar).toHaveClass('h-16');
    expect(avatar).toHaveClass('w-16');
  });

  it('should apply 2xl size classes', () => {
    render(<Avatar size="2xl" data-testid="avatar" fallback="Test" />);
    const avatar = screen.getByTestId('avatar');
    
    expect(avatar).toHaveClass('h-24');
    expect(avatar).toHaveClass('w-24');
  });

  it('should apply custom className', () => {
    render(<Avatar className="custom-class" data-testid="avatar" fallback="Test" />);
    expect(screen.getByTestId('avatar')).toHaveClass('custom-class');
  });

  it('should have rounded-full class', () => {
    render(<Avatar data-testid="avatar" fallback="Test" />);
    expect(screen.getByTestId('avatar')).toHaveClass('rounded-full');
  });

  it('should forward ref correctly', () => {
    const ref = { current: null } as React.MutableRefObject<HTMLSpanElement | null>;
    render(<Avatar ref={ref} fallback="Test" />);
    expect(ref.current).not.toBeNull();
  });

  it('should show fallback when image fails to load', async () => {
    render(
      <Avatar src="https://example.com/invalid.jpg" fallback="John Doe" />
    );
    
    // Initially shows image
    const img = screen.getByRole('img');
    expect(img).toBeInTheDocument();
    
    // Simulate image error using fireEvent
    fireEvent.error(img);
    
    // Wait for state update and fallback to show
    await waitFor(() => {
      expect(screen.getByText('JD')).toBeInTheDocument();
    });
  });
});
