import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Switch } from '../switch';

describe('Switch', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(async () => {
    await act(async () => {
      jest.runOnlyPendingTimers();
    });
    jest.useRealTimers();
  });

  it('should render a switch', () => {
    render(<Switch aria-label="Test switch" />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('should be unchecked by default', () => {
    render(<Switch aria-label="Test switch" />);
    expect(screen.getByRole('switch')).not.toBeChecked();
  });

  it('should be checked when defaultChecked is true', () => {
    render(<Switch defaultChecked aria-label="Test switch" />);
    expect(screen.getByRole('switch')).toBeChecked();
  });

  it('should toggle on click', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<Switch aria-label="Test switch" />);
    
    const switchEl = screen.getByRole('switch');
    expect(switchEl).not.toBeChecked();
    
    await act(async () => {
      await user.click(switchEl);
      jest.runOnlyPendingTimers();
    });
    expect(switchEl).toBeChecked();
    
    await act(async () => {
      await user.click(switchEl);
      jest.runOnlyPendingTimers();
    });
    expect(switchEl).not.toBeChecked();
  });

  it('should call onCheckedChange when toggled', async () => {
    const handleChange = jest.fn();
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    
    render(<Switch onCheckedChange={handleChange} aria-label="Test switch" />);
    
    await act(async () => {
      await user.click(screen.getByRole('switch'));
      jest.runOnlyPendingTimers();
    });

    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('should be disabled when disabled prop is true', () => {
    render(<Switch disabled aria-label="Test switch" />);
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('should not toggle when disabled', async () => {
    const handleChange = jest.fn();
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    
    render(<Switch disabled onCheckedChange={handleChange} aria-label="Test switch" />);
    
    await act(async () => {
      await user.click(screen.getByRole('switch'));
      jest.runOnlyPendingTimers();
    });
    
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('should apply custom className', () => {
    render(<Switch className="custom-class" aria-label="Test switch" />);
    expect(screen.getByRole('switch')).toHaveClass('custom-class');
  });

  it('should have correct size classes', () => {
    render(<Switch aria-label="Test switch" />);
    const switchEl = screen.getByRole('switch');
    
    expect(switchEl).toHaveClass('h-5');
    expect(switchEl).toHaveClass('w-10');
  });

  it('should forward ref correctly', () => {
    const ref = { current: null } as React.MutableRefObject<HTMLButtonElement | null>;
    render(<Switch ref={ref} aria-label="Test switch" />);
    expect(ref.current).not.toBeNull();
  });

  it('should support controlled checked state', async () => {
    const handleChange = jest.fn();
    
    const { rerender } = render(
      <Switch checked={false} onCheckedChange={handleChange} aria-label="Test switch" />
    );
    
    expect(screen.getByRole('switch')).not.toBeChecked();
    
    rerender(
      <Switch checked={true} onCheckedChange={handleChange} aria-label="Test switch" />
    );
    
    expect(screen.getByRole('switch')).toBeChecked();
  });
});
