import React from 'react';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent } from '../card';

describe('Card', () => {
  it('renders Card with children', () => {
    render(<Card>Card Content</Card>);
    expect(screen.getByText('Card Content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Card className="custom-card" data-testid="card">Content</Card>);
    expect(screen.getByTestId('card')).toHaveClass('custom-card');
  });

  it('applies base card styles', () => {
    render(<Card data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveClass('rounded-rams-sm');
    expect(card).toHaveClass('border-rams-line');
  });
});

describe('CardHeader', () => {
  it('renders CardHeader with children', () => {
    render(<CardHeader>Header Content</CardHeader>);
    expect(screen.getByText('Header Content')).toBeInTheDocument();
  });

  it('applies spacing styles', () => {
    render(<CardHeader data-testid="header">Header</CardHeader>);
    const header = screen.getByTestId('header');
    expect(header).toHaveClass('p-5');
  });
});

describe('CardTitle', () => {
  it('renders CardTitle with text', () => {
    render(<CardTitle>My Title</CardTitle>);
    expect(screen.getByText('My Title')).toBeInTheDocument();
  });

  it('applies heading styles', () => {
    render(<CardTitle data-testid="title">Title</CardTitle>);
    const title = screen.getByTestId('title');
    expect(title).toHaveClass('font-black');
    expect(title).toHaveClass('uppercase');
  });
});

describe('CardDescription', () => {
  it('renders CardDescription with text', () => {
    render(<CardDescription>Description text</CardDescription>);
    expect(screen.getByText('Description text')).toBeInTheDocument();
  });

  it('applies muted text styles', () => {
    render(<CardDescription data-testid="desc">Desc</CardDescription>);
    expect(screen.getByTestId('desc')).toHaveClass('text-muted-foreground/60');
  });
});

describe('CardContent', () => {
  it('renders CardContent with children', () => {
    render(<CardContent>Content here</CardContent>);
    expect(screen.getByText('Content here')).toBeInTheDocument();
  });

  it('applies padding styles', () => {
    render(<CardContent data-testid="content">Content</CardContent>);
    expect(screen.getByTestId('content')).toHaveClass('p-5');
  });
});

describe('CardFooter', () => {
  it('renders CardFooter with children', () => {
    render(<CardFooter>Footer Content</CardFooter>);
    expect(screen.getByText('Footer Content')).toBeInTheDocument();
  });

  it('applies flex layout', () => {
    render(<CardFooter data-testid="footer">Footer</CardFooter>);
    const footer = screen.getByTestId('footer');
    expect(footer).toHaveClass('flex');
    expect(footer).toHaveClass('items-center');
  });
});

describe('Complete Card', () => {
  it('renders a complete card structure', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card description goes here</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Main content of the card</p>
        </CardContent>
        <CardFooter>
          <button>Action</button>
        </CardFooter>
      </Card>
    );

    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card description goes here')).toBeInTheDocument();
    expect(screen.getByText('Main content of the card')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });
});
