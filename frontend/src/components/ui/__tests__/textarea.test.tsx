import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from '../textarea';

describe('Textarea', () => {
  it('should render a textarea element', () => {
    render(<Textarea placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('should accept user input', async () => {
    const user = userEvent.setup();
    render(<Textarea placeholder="Enter text" />);
    
    const textarea = screen.getByPlaceholderText('Enter text');
    await user.type(textarea, 'Hello World');
    
    expect(textarea).toHaveValue('Hello World');
  });

  it('should handle multiline input', async () => {
    const user = userEvent.setup();
    render(<Textarea placeholder="Enter text" />);
    
    const textarea = screen.getByPlaceholderText('Enter text');
    await user.type(textarea, 'Line 1{enter}Line 2');
    
    expect(textarea).toHaveValue('Line 1\nLine 2');
  });

  it('should apply custom className', () => {
    render(<Textarea className="custom-class" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('custom-class');
  });

  it('should show error state', () => {
    render(<Textarea error data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('border-danger');
  });

  it('should handle different resize options', () => {
    const { rerender } = render(<Textarea resize="none" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('resize-none');

    rerender(<Textarea resize="vertical" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('resize-y');

    rerender(<Textarea resize="horizontal" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('resize-x');

    rerender(<Textarea resize="both" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('resize');
  });

  it('should default to vertical resize', () => {
    render(<Textarea data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('resize-y');
  });

  it('should be disabled when disabled prop is true', () => {
    render(<Textarea disabled placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeDisabled();
  });

  it('should be required when required prop is true', () => {
    render(<Textarea required placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeRequired();
  });

  it('should be readonly when readOnly prop is true', () => {
    render(<Textarea readOnly value="Readonly text" placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toHaveAttribute('readonly');
  });

  it('should forward ref correctly', () => {
    const ref = { current: null } as React.MutableRefObject<HTMLTextAreaElement | null>;
    render(<Textarea ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
  });

  it('should support onChange handler', async () => {
    const handleChange = jest.fn();
    const user = userEvent.setup();
    
    render(<Textarea onChange={handleChange} placeholder="Enter text" />);
    const textarea = screen.getByPlaceholderText('Enter text');
    
    await user.type(textarea, 'Test');
    
    expect(handleChange).toHaveBeenCalled();
  });

  it('should support rows attribute', () => {
    render(<Textarea rows={5} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('rows', '5');
  });

  it('should support maxLength attribute', () => {
    render(<Textarea maxLength={100} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('maxLength', '100');
  });
});
