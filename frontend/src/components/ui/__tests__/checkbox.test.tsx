import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Checkbox } from '../checkbox';

describe('Checkbox', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(async () => {
    await act(async () => {
      jest.runOnlyPendingTimers();
    });
    jest.useRealTimers();
  });

  it('should render a checkbox', () => {
    render(<Checkbox aria-label="Test checkbox" />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('should be unchecked by default', () => {
    render(<Checkbox aria-label="Test checkbox" />);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('should be checked when defaultChecked is true', () => {
    render(<Checkbox defaultChecked aria-label="Test checkbox" />);
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('should toggle on click', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<Checkbox aria-label="Test checkbox" />);
    
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).not.toBeChecked();
    
    await act(async () => {
      await user.click(checkbox);
      jest.runOnlyPendingTimers();
    });
    expect(checkbox).toBeChecked();
    
    await act(async () => {
      await user.click(checkbox);
      jest.runOnlyPendingTimers();
    });
    expect(checkbox).not.toBeChecked();
  });

  it('should call onCheckedChange when toggled', async () => {
    const handleChange = jest.fn();
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    
    render(<Checkbox onCheckedChange={handleChange} aria-label="Test checkbox" />);
    
    await act(async () => {
      await user.click(screen.getByRole('checkbox'));
      jest.runOnlyPendingTimers();
    });

    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('should be disabled when disabled prop is true', () => {
    render(<Checkbox disabled aria-label="Test checkbox" />);
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  it('should not toggle when disabled', async () => {
    const handleChange = jest.fn();
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    
    render(<Checkbox disabled onCheckedChange={handleChange} aria-label="Test checkbox" />);
    
    await act(async () => {
      await user.click(screen.getByRole('checkbox'));
      jest.runOnlyPendingTimers();
    });
    
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('should apply custom className', () => {
    render(<Checkbox className="custom-class" aria-label="Test checkbox" />);
    expect(screen.getByRole('checkbox')).toHaveClass('custom-class');
  });

  it('should have correct size classes', () => {
    render(<Checkbox aria-label="Test checkbox" />);
    const checkbox = screen.getByRole('checkbox');
    
    expect(checkbox).toHaveClass('h-4');
    expect(checkbox).toHaveClass('w-4');
  });

  it('should forward ref correctly', () => {
    const ref = { current: null } as React.MutableRefObject<HTMLButtonElement | null>;
    render(<Checkbox ref={ref} aria-label="Test checkbox" />);
    expect(ref.current).not.toBeNull();
  });

  it('should support controlled checked state', async () => {
    const handleChange = jest.fn();
    
    const { rerender } = render(
      <Checkbox checked={false} onCheckedChange={handleChange} aria-label="Test checkbox" />
    );
    
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    
    rerender(
      <Checkbox checked={true} onCheckedChange={handleChange} aria-label="Test checkbox" />
    );
    
    expect(screen.getByRole('checkbox')).toBeChecked();
  });
});
