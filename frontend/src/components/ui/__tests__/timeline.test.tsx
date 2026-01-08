import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  Timeline,
  TimelineItem,
  TimelineIcon,
  TimelineContent,
  TimelineHeader,
  TimelineTitle,
  TimelineDescription,
  TimelineTimestamp,
  TimelineDetails,
  TimelineUser,
  TimelineEmptyState,
  TimelineLoadingState,
  TimelineGroup,
  TimelineItemCard,
} from '../timeline';

describe('Timeline', () => {
  describe('Basic Timeline Structure', () => {
    it('renders timeline with items', () => {
      render(
        <Timeline>
          <TimelineItem>
            <TimelineIcon />
            <TimelineContent>
              <TimelineTitle>Event 1</TimelineTitle>
            </TimelineContent>
          </TimelineItem>
          <TimelineItem>
            <TimelineIcon />
            <TimelineContent>
              <TimelineTitle>Event 2</TimelineTitle>
            </TimelineContent>
          </TimelineItem>
        </Timeline>
      );

      expect(screen.getByText('Event 1')).toBeInTheDocument();
      expect(screen.getByText('Event 2')).toBeInTheDocument();
    });

    it('applies variant spacing', () => {
      const { container } = render(
        <Timeline variant="compact">
          <TimelineItem>
            <TimelineIcon />
            <TimelineContent>
              <TimelineTitle>Event</TimelineTitle>
            </TimelineContent>
          </TimelineItem>
        </Timeline>
      );

      const timeline = container.firstChild;
      expect(timeline).toHaveClass('space-y-3');
    });

    it('renders with detailed variant', () => {
      const { container } = render(
        <Timeline variant="detailed">
          <TimelineItem>
            <TimelineIcon />
            <TimelineContent>
              <TimelineTitle>Event</TimelineTitle>
            </TimelineContent>
          </TimelineItem>
        </Timeline>
      );

      const timeline = container.firstChild;
      expect(timeline).toHaveClass('space-y-8');
    });

    it('has proper ARIA role', () => {
      const { container } = render(
        <Timeline>
          <TimelineItem>
            <TimelineIcon />
            <TimelineContent>
              <TimelineTitle>Event</TimelineTitle>
            </TimelineContent>
          </TimelineItem>
        </Timeline>
      );

      const timeline = container.firstChild;
      expect(timeline).toHaveAttribute('role', 'list');
    });
  });

  describe('TimelineItem', () => {
    it('renders with timeline line', () => {
      const { container } = render(
        <TimelineItem>
          <TimelineIcon />
          <TimelineContent>
            <TimelineTitle>Event</TimelineTitle>
          </TimelineContent>
        </TimelineItem>
      );

      const line = container.querySelector('.absolute.left-4');
      expect(line).toBeInTheDocument();
    });

    it('does not render line for last item', () => {
      const { container } = render(
        <TimelineItem last>
          <TimelineIcon />
          <TimelineContent>
            <TimelineTitle>Last Event</TimelineTitle>
          </TimelineContent>
        </TimelineItem>
      );

      const line = container.querySelector('.absolute.left-4');
      expect(line).not.toBeInTheDocument();
    });

    it('renders active state', () => {
      const { container } = render(
        <TimelineItem active>
          <TimelineIcon />
          <TimelineContent>
            <TimelineTitle>Active Event</TimelineTitle>
          </TimelineContent>
        </TimelineItem>
      );

      const line = container.querySelector('.bg-primary');
      expect(line).toBeInTheDocument();
    });

    it('has proper ARIA role', () => {
      const { container } = render(
        <TimelineItem>
          <TimelineIcon />
          <TimelineContent>
            <TimelineTitle>Event</TimelineTitle>
          </TimelineContent>
        </TimelineItem>
      );

      const item = container.firstChild;
      expect(item).toHaveAttribute('role', 'listitem');
    });
  });

  describe('TimelineIcon', () => {
    it('renders default icon', () => {
      const { container } = render(<TimelineIcon />);

      const dot = container.querySelector('.rounded-full.bg-muted-foreground');
      expect(dot).toBeInTheDocument();
    });

    it('renders custom icon', () => {
      render(
        <TimelineIcon>
          <span data-testid="custom-icon">✓</span>
        </TimelineIcon>
      );

      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('applies success variant', () => {
      const { container } = render(<TimelineIcon variant="success" />);

      const icon = container.firstChild;
      expect(icon).toHaveClass('border-green-500');
    });

    it('applies warning variant', () => {
      const { container } = render(<TimelineIcon variant="warning" />);

      const icon = container.firstChild;
      expect(icon).toHaveClass('border-yellow-500');
    });

    it('applies danger variant', () => {
      const { container } = render(<TimelineIcon variant="danger" />);

      const icon = container.firstChild;
      expect(icon).toHaveClass('border-red-500');
    });

    it('applies info variant', () => {
      const { container } = render(<TimelineIcon variant="info" />);

      const icon = container.firstChild;
      expect(icon).toHaveClass('border-blue-500');
    });

    it('renders active state', () => {
      const { container } = render(<TimelineIcon active />);

      const icon = container.firstChild;
      expect(icon).toHaveClass('border-primary', 'bg-primary');
    });
  });

  describe('TimelineContent', () => {
    it('renders timeline content', () => {
      render(
        <TimelineContent>
          <TimelineTitle>Title</TimelineTitle>
          <TimelineDescription>Description</TimelineDescription>
        </TimelineContent>
      );

      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      const { container } = render(
        <TimelineContent className="custom-class">
          <div>Content</div>
        </TimelineContent>
      );

      const content = container.firstChild;
      expect(content).toHaveClass('custom-class');
    });
  });

  describe('TimelineHeader', () => {
    it('renders header with title and timestamp', () => {
      render(
        <TimelineHeader>
          <TimelineTitle>Event Title</TimelineTitle>
          <TimelineTimestamp timestamp={new Date('2024-01-01')} relative={false} />
        </TimelineHeader>
      );

      expect(screen.getByText('Event Title')).toBeInTheDocument();
    });
  });

  describe('TimelineTimestamp', () => {
    it('renders relative time by default', () => {
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      
      render(<TimelineTimestamp timestamp={oneHourAgo} />);

      // Should show something like "1 hour ago"
      const timestamp = screen.getByText(/ago|hour/i);
      expect(timestamp).toBeInTheDocument();
    });

    it('renders absolute time when relative is false', () => {
      const date = new Date('2024-01-15T10:30:00');
      
      render(<TimelineTimestamp timestamp={date} relative={false} />);

      // Should show formatted date
      const timestamp = screen.getByText(/Jan|2024/i);
      expect(timestamp).toBeInTheDocument();
    });

    it('accepts string timestamp', () => {
      render(<TimelineTimestamp timestamp="2024-01-01T00:00:00Z" relative={false} />);

      const timestamp = screen.getByText(/2024|Jan/i);
      expect(timestamp).toBeInTheDocument();
    });

    it('has title attribute with full date', () => {
      const { container } = render(
        <TimelineTimestamp timestamp={new Date('2024-01-01')} />
      );

      const timestamp = container.querySelector('span');
      expect(timestamp).toHaveAttribute('title');
    });
  });

  describe('TimelineDetails', () => {
    it('renders details without collapsible', () => {
      render(
        <TimelineDetails>
          <div>Detail content</div>
        </TimelineDetails>
      );

      expect(screen.getByText('Detail content')).toBeInTheDocument();
    });

    it('renders collapsible details', () => {
      render(
        <TimelineDetails collapsible>
          <div>Collapsible content</div>
        </TimelineDetails>
      );

      expect(screen.getByText('Show details')).toBeInTheDocument();
      expect(screen.queryByText('Collapsible content')).not.toBeInTheDocument();
    });

    it('toggles collapsible details', () => {
      render(
        <TimelineDetails collapsible>
          <div>Collapsible content</div>
        </TimelineDetails>
      );

      const button = screen.getByText('Show details');
      fireEvent.click(button);

      expect(screen.getByText('Collapsible content')).toBeInTheDocument();
      expect(screen.getByText('Hide details')).toBeInTheDocument();

      fireEvent.click(screen.getByText('Hide details'));
      expect(screen.queryByText('Collapsible content')).not.toBeInTheDocument();
    });

    it('renders open by default when specified', () => {
      render(
        <TimelineDetails collapsible defaultOpen>
          <div>Default open content</div>
        </TimelineDetails>
      );

      expect(screen.getByText('Default open content')).toBeInTheDocument();
      expect(screen.getByText('Hide details')).toBeInTheDocument();
    });
  });

  describe('TimelineUser', () => {
    it('renders user with name', () => {
      render(<TimelineUser name="John Doe" />);

      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('renders user with avatar', () => {
      render(<TimelineUser name="John Doe" avatar="https://example.com/avatar.jpg" />);

      const avatar = screen.getByAltText('John Doe');
      expect(avatar).toBeInTheDocument();
      expect(avatar).toHaveAttribute('src', 'https://example.com/avatar.jpg');
    });

    it('renders initials when no avatar', () => {
      render(<TimelineUser name="John Doe" />);

      expect(screen.getByText('J')).toBeInTheDocument();
    });
  });

  describe('TimelineEmptyState', () => {
    it('renders default empty state', () => {
      render(<TimelineEmptyState />);

      expect(screen.getByText('No activity yet')).toBeInTheDocument();
      expect(screen.getByText(/Activity will appear here/i)).toBeInTheDocument();
    });

    it('renders custom title and description', () => {
      render(
        <TimelineEmptyState
          title="No events found"
          description="Events will show up here"
        />
      );

      expect(screen.getByText('No events found')).toBeInTheDocument();
      expect(screen.getByText('Events will show up here')).toBeInTheDocument();
    });

    it('renders custom icon', () => {
      render(
        <TimelineEmptyState
          icon={<span data-testid="custom-icon">📅</span>}
        />
      );

      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('renders action button', () => {
      render(
        <TimelineEmptyState
          action={<button>Create Event</button>}
        />
      );

      expect(screen.getByText('Create Event')).toBeInTheDocument();
    });
  });

  describe('TimelineLoadingState', () => {
    it('renders loading skeleton', () => {
      const { container } = render(<TimelineLoadingState />);

      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('renders custom number of items', () => {
      const { container } = render(<TimelineLoadingState items={5} />);

      const items = container.querySelectorAll('.flex.gap-4');
      expect(items).toHaveLength(5);
    });
  });

  describe('TimelineGroup', () => {
    it('renders group with label', () => {
      render(
        <TimelineGroup label="Today">
          <TimelineItem>
            <TimelineIcon />
            <TimelineContent>
              <TimelineTitle>Event</TimelineTitle>
            </TimelineContent>
          </TimelineItem>
        </TimelineGroup>
      );

      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Event')).toBeInTheDocument();
    });

    it('has sticky label', () => {
      const { container } = render(
        <TimelineGroup label="Today">
          <div>Content</div>
        </TimelineGroup>
      );

      const label = screen.getByText('Today').parentElement;
      expect(label).toHaveClass('sticky');
    });
  });

  describe('TimelineItemCard', () => {
    const baseProps = {
      id: '1',
      timestamp: new Date('2024-01-01T10:00:00'),
      title: 'Event Title',
    };

    it('renders complete timeline item', () => {
      render(<TimelineItemCard {...baseProps} />);

      expect(screen.getByText('Event Title')).toBeInTheDocument();
    });

    it('renders with description', () => {
      render(
        <TimelineItemCard {...baseProps} description="Event description" />
      );

      expect(screen.getByText('Event description')).toBeInTheDocument();
    });

    it('renders with user', () => {
      render(
        <TimelineItemCard
          {...baseProps}
          user={{ name: 'John Doe', avatar: 'https://example.com/avatar.jpg' }}
        />
      );

      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('renders with custom icon', () => {
      render(
        <TimelineItemCard
          {...baseProps}
          icon={<span data-testid="custom-icon">✓</span>}
        />
      );

      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('renders with details', () => {
      render(
        <TimelineItemCard
          {...baseProps}
          details={<div>Additional details</div>}
        />
      );

      expect(screen.getByText('Additional details')).toBeInTheDocument();
    });

    it('renders with collapsible details', () => {
      render(
        <TimelineItemCard
          {...baseProps}
          details={<div>Collapsible details</div>}
          collapsibleDetails
        />
      );

      expect(screen.getByText('Show details')).toBeInTheDocument();
      expect(screen.queryByText('Collapsible details')).not.toBeInTheDocument();
    });

    it('applies success variant for approval type', () => {
      const { container } = render(
        <TimelineItemCard {...baseProps} type="approval" />
      );

      const icon = container.querySelector('.border-green-500');
      expect(icon).toBeInTheDocument();
    });

    it('applies danger variant for rejection type', () => {
      const { container } = render(
        <TimelineItemCard {...baseProps} type="rejection" />
      );

      const icon = container.querySelector('.border-red-500');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Integration Example', () => {
    it('renders complete timeline with multiple items', () => {
      const events = [
        {
          id: '1',
          timestamp: new Date('2024-01-01T10:00:00'),
          title: 'Quote Approved',
          description: 'Quote #12345 was approved by manager',
          user: { name: 'Jane Smith' },
          type: 'approval' as const,
        },
        {
          id: '2',
          timestamp: new Date('2024-01-01T09:00:00'),
          title: 'Quote Submitted',
          description: 'Quote submitted for approval',
          user: { name: 'John Doe' },
          type: 'event' as const,
        },
      ];

      render(
        <Timeline>
          {events.map((event, index) => (
            <TimelineItemCard
              key={event.id}
              {...event}
              last={index === events.length - 1}
            />
          ))}
        </Timeline>
      );

      expect(screen.getByText('Quote Approved')).toBeInTheDocument();
      expect(screen.getByText('Quote Submitted')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('renders grouped timeline', () => {
      render(
        <Timeline>
          <TimelineGroup label="Today">
            <TimelineItemCard
              id="1"
              timestamp={new Date()}
              title="Recent Event"
            />
          </TimelineGroup>
          <TimelineGroup label="Yesterday">
            <TimelineItemCard
              id="2"
              timestamp={new Date(Date.now() - 86400000)}
              title="Old Event"
            />
          </TimelineGroup>
        </Timeline>
      );

      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
      expect(screen.getByText('Recent Event')).toBeInTheDocument();
      expect(screen.getByText('Old Event')).toBeInTheDocument();
    });
  });
});
