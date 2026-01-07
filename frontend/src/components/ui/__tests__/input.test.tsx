import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../input';

describe('Input', () => {
  it('renders with default props', () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('accepts user input', async () => {
    const user = userEvent.setup();
    render(<Input placeholder="Type here" />);
    
    const input = screen.getByPlaceholderText('Type here');
    await user.type(input, 'Hello World');
    
    expect(input).toHaveValue('Hello World');
  });

  it('can be disabled', async () => {
    const user = userEvent.setup();
    render(<Input placeholder="Disabled" disabled />);
    
    const input = screen.getByPlaceholderText('Disabled');
    expect(input).toBeDisabled();
    
    await user.type(input, 'test');
    expect(input).not.toHaveValue('test');
  });

  it('supports different types', () => {
    const { rerender } = render(<Input type="text" data-testid="input" />);
    expect(screen.getByTestId('input')).toHaveAttribute('type', 'text');

    rerender(<Input type="email" data-testid="input" />);
    expect(screen.getByTestId('input')).toHaveAttribute('type', 'email');

    rerender(<Input type="password" data-testid="input" />);
    expect(screen.getByTestId('input')).toHaveAttribute('type', 'password');

    rerender(<Input type="number" data-testid="input" />);
    expect(screen.getByTestId('input')).toHaveAttribute('type', 'number');
  });

  it('applies custom className', () => {
    render(<Input className="custom-input" data-testid="input" />);
    expect(screen.getByTestId('input')).toHaveClass('custom-input');
  });

  it('forwards ref correctly', () => {
    const ref = React.createRef<HTMLInputElement>();
    render(<Input ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });

  it('handles onChange events', async () => {
    const user = userEvent.setup();
    const handleChange = jest.fn();
    
    render(<Input onChange={handleChange} placeholder="Input" />);
    
    await user.type(screen.getByPlaceholderText('Input'), 'a');
    
    expect(handleChange).toHaveBeenCalled();
  });

  it('applies focus styles', () => {
    render(<Input data-testid="input" />);
    const input = screen.getByTestId('input');
    
    // Check that focus-visible styles are defined
    expect(input.className).toContain('focus-visible:');
  });

  it('handles required attribute', () => {
    render(<Input required data-testid="input" />);
    expect(screen.getByTestId('input')).toBeRequired();
  });

  it('handles readonly attribute', () => {
    render(<Input readOnly value="readonly value" data-testid="input" />);
    expect(screen.getByTestId('input')).toHaveAttribute('readonly');
  });
});
