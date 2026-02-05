import { render, screen } from '@testing-library/react';
import { Label } from '../label';

describe('Label', () => {
  it('should render a label element', () => {
    render(<Label>Test Label</Label>);
    expect(screen.getByText('Test Label')).toBeInTheDocument();
  });

  it('should apply default variant styles', () => {
    render(<Label data-testid="label">Test Label</Label>);
    expect(screen.getByTestId('label')).toHaveClass('text-foreground/70');
  });

  it('should apply muted variant styles', () => {
    render(<Label variant="muted" data-testid="label">Test Label</Label>);
    expect(screen.getByTestId('label')).toHaveClass('text-muted-foreground/50');
  });

  it('should apply error variant styles', () => {
    render(<Label variant="error" data-testid="label">Test Label</Label>);
    expect(screen.getByTestId('label')).toHaveClass('text-rams-red');
  });

  it('should show required indicator when required is true', () => {
    render(<Label required>Test Label</Label>);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('should not show required indicator when required is false', () => {
    render(<Label>Test Label</Label>);
    expect(screen.queryByText('*')).not.toBeInTheDocument();
  });

  it('should apply custom className', () => {
    render(<Label className="custom-class" data-testid="label">Test Label</Label>);
    expect(screen.getByTestId('label')).toHaveClass('custom-class');
  });

  it('should have base styles', () => {
    render(<Label data-testid="label">Test Label</Label>);
    const label = screen.getByTestId('label');
    
    expect(label).toHaveClass('text-[10px]');
    expect(label).toHaveClass('font-black');
    expect(label).toHaveClass('leading-none');
  });

  it('should associate with an input via htmlFor', () => {
    render(
      <>
        <Label htmlFor="test-input">Test Label</Label>
        <input id="test-input" />
      </>
    );
    
    const label = screen.getByText('Test Label');
    expect(label).toHaveAttribute('for', 'test-input');
  });

  it('should forward ref correctly', () => {
    const ref = { current: null } as React.MutableRefObject<HTMLLabelElement | null>;
    render(<Label ref={ref}>Test Label</Label>);
    expect(ref.current).not.toBeNull();
  });
});
