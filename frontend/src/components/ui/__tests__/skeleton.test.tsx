import { render, screen } from '@testing-library/react';
import { Skeleton } from '../skeleton';

describe('Skeleton', () => {
  it('should render with default classes', () => {
    render(<Skeleton data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    
    expect(skeleton).toHaveClass('animate-pulse');
    expect(skeleton).toHaveClass('rounded-md');
    expect(skeleton).toHaveClass('bg-muted');
  });

  it('should apply custom className', () => {
    render(<Skeleton className="custom-class h-10 w-10" data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    
    expect(skeleton).toHaveClass('custom-class');
    expect(skeleton).toHaveClass('h-10');
    expect(skeleton).toHaveClass('w-10');
  });

  it('should pass through additional props', () => {
    render(<Skeleton data-testid="skeleton" id="test-skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveAttribute('id', 'test-skeleton');
  });

  it('should render as a div element', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton').tagName).toBe('DIV');
  });

  it('should accept inline styles', () => {
    render(<Skeleton data-testid="skeleton" style={{ width: '100px' }} />);
    expect(screen.getByTestId('skeleton')).toHaveStyle({ width: '100px' });
  });
});
