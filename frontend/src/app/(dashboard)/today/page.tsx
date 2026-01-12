'use client';

import * as React from 'react';
import Link from 'next/link';

import { Calendar, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores';

type PriorityLevel = 'low' | 'medium' | 'high' | 'urgent';

type PriorityItem = {
	id: string;
	title: string;
	priority: PriorityLevel;
	href: string;
};

type TaskItem = {
	id: string;
	title: string;
	dueLabel: string;
	href: string;
};

type ActivityItem = {
	id: string;
	text: string;
	when: string;
	href?: string;
};

type RFQItem = {
	id: string;
	title: string;
	customer: string;
	priority: PriorityLevel;
	status: string;
	href: string;
};

type KpiItem = {
	id: string;
	title: string;
	value: number;
	trendLabel: string;
	href: string;
};

function formatHeaderDate(date: Date): string {
	return date.toLocaleDateString('en-US', {
		weekday: 'long',
		month: 'long',
		day: 'numeric',
	});
}

function priorityBadgeVariant(priority: PriorityLevel): 'default' | 'secondary' | 'destructive' {
	if (priority === 'urgent') return 'destructive';
	if (priority === 'high') return 'default';
	return 'secondary';
}

export default function TodayPage() {
	const { user } = useAuthStore();

	const firstName = user?.full_name?.split(' ')[0] || 'there';

	const priorities: PriorityItem[] = [
		{
			id: 'p1',
			title: 'Close RFQ blockers for today',
			priority: 'urgent',
			href: '/pipeline/priority',
		},
		{
			id: 'p2',
			title: 'Confirm production schedule risks',
			priority: 'high',
			href: '/tasks/production-schedule',
		},
		{
			id: 'p3',
			title: 'Review top quality abnormalities',
			priority: 'medium',
			href: '/tasks/quality-abnormalities',
		},
	];

	const tasks: TaskItem[] = [
		{
			id: 't1',
			title: 'Approve quote draft for customer',
			dueLabel: 'Due today',
			href: '/tasks/quote-approval',
		},
		{
			id: 't2',
			title: 'Daily Gemba walk notes',
			dueLabel: 'Due in 2 hours',
			href: '/tasks/gemba',
		},
	];

	const activity: ActivityItem[] = [
		{
			id: 'a1',
			text: 'RFQ moved to Quoting by John',
			when: '2 hours ago',
			href: '/pipeline',
		},
		{
			id: 'a2',
			text: 'New NCR created by QA',
			when: '4 days ago',
			href: '/quality',
		},
	];

	const rfqs: RFQItem[] = [
		{
			id: 'r1',
			title: 'Machined bracket assembly',
			customer: 'ACME',
			priority: 'high',
			status: 'reviewing',
			href: '/pipeline/r1',
		},
		{
			id: 'r2',
			title: 'Welded frame revision',
			customer: 'Globex',
			priority: 'urgent',
			status: 'new',
			href: '/pipeline/r2',
		},
	];

	const kpis: KpiItem[] = [
		{
			id: 'k1',
			title: 'Open RFQs',
			value: 12,
			trendLabel: 'Up 4 from last week',
			href: '/pipeline',
		},
		{
			id: 'k2',
			title: 'Pending Quotes',
			value: 5,
			trendLabel: 'Down 4 from last week',
			href: '/pipeline',
		},
		{
			id: 'k3',
			title: 'Late Tasks',
			value: 10,
			trendLabel: 'Same as last week',
			href: '/tasks',
		},
		{
			id: 'k4',
			title: 'Active Abnormalities',
			value: 4,
			trendLabel: 'Up 4 from last week',
			href: '/quality',
		},
	];

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-3xl font-bold">Hello, {firstName}!</h1>
					<p className="text-muted-foreground">
						<Calendar className="inline-block h-4 w-4 mr-1" />
						{formatHeaderDate(new Date())}
					</p>
				</div>

				{/* KPI Cards */}
				<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
					{kpis.map((kpi) => (
						<Card key={kpi.id}>
							<CardHeader className="space-y-1">
								<Link href={kpi.href} className="block rounded-md focus:outline-none focus:ring-2 focus:ring-ring">
									<CardTitle className="text-sm font-medium">{kpi.title}</CardTitle>
									<div className="text-2xl font-bold">{kpi.value}</div>
									<CardDescription>{kpi.trendLabel}</CardDescription>
								</Link>
							</CardHeader>
						</Card>
					))}
				</div>

				<Button asChild>
					<Link href="/pipeline/new">Create RFQ</Link>
				</Button>
			</div>

			<div className="grid gap-6 lg:grid-cols-3">
				<article className="lg:col-span-2">
					<Card>
						<CardHeader>
							<CardTitle>Top 3 Priorities</CardTitle>
							<CardDescription>Your focus items for today</CardDescription>
						</CardHeader>
						<CardContent className="space-y-3">
							{priorities.map((p, idx) => (
								<div key={p.id} className="flex items-start justify-between gap-3">
									<div className="flex items-start gap-3">
										<div className="mt-0.5 w-6 h-6 rounded-full border flex items-center justify-center text-sm font-semibold">
											{idx + 1}
										</div>
										<div className="space-y-1">
											<Link href={p.href} className="font-medium hover:underline">
												{p.title}
											</Link>
											<Badge role="status" variant={priorityBadgeVariant(p.priority)}>
												{p.priority}
											</Badge>
										</div>
									</div>
									<Button variant="ghost" size="sm" asChild>
										<Link href={p.href}>
											Open <ArrowRight className="ml-2 h-4 w-4" />
										</Link>
									</Button>
								</div>
							))}
						</CardContent>
					</Card>
				</article>

				<article>
					<Card>
						<CardHeader>
							<CardTitle>My Tasks</CardTitle>
							<CardDescription>Due today and upcoming</CardDescription>
						</CardHeader>
						<CardContent className="space-y-3">
							{tasks.map((t) => (
								<div key={t.id} className="flex items-start gap-3">
									<CheckCircle2 className="h-4 w-4 text-muted-foreground mt-1" />
									<div className="space-y-1">
										<Link href={t.href} className="font-medium hover:underline">
											{t.title}
										</Link>
										<p className="text-xs text-muted-foreground">{t.dueLabel}</p>
									</div>
								</div>
							))}
							{tasks.length === 0 && (
								<p className="text-sm text-muted-foreground">No tasks</p>
							)}
							<div className="pt-2">
								<Button variant="ghost" size="sm" asChild>
									<Link href="/tasks">
										View All <ArrowRight className="ml-2 h-4 w-4" />
									</Link>
								</Button>
							</div>
						</CardContent>
					</Card>
				</article>

				<article className="lg:col-span-2">
					<Card>
						<CardHeader>
							<CardTitle>Recent Activity</CardTitle>
							<CardDescription>What changed recently</CardDescription>
						</CardHeader>
						<CardContent className="space-y-3">
							{activity.map((a) => (
								<div key={a.id} className="flex items-start justify-between gap-3 text-sm">
									<div className="flex items-start gap-2">
										<AlertCircle className="h-4 w-4 text-muted-foreground mt-0.5" />
										{a.href ? (
											<Link href={a.href} className="hover:underline">
												{a.text}
											</Link>
										) : (
											<span>{a.text}</span>
										)}
									</div>
									<span className="text-xs text-muted-foreground">{a.when}</span>
								</div>
							))}
						</CardContent>
					</Card>
				</article>

				<article>
					<Card>
						<CardHeader className="flex flex-row items-center justify-between">
							<div>
								<CardTitle>Priority RFQs</CardTitle>
								<CardDescription>Focus RFQs that need attention</CardDescription>
							</div>
							<Button variant="ghost" size="sm" asChild>
								<Link href="/pipeline">View Pipeline</Link>
							</Button>
						</CardHeader>
						<CardContent className="space-y-3">
							{rfqs.map((r) => (
								<div key={r.id} className="space-y-1">
									<Link href={r.href} className="font-medium hover:underline">
										{r.customer}: {r.title}
									</Link>
									<div className="flex items-center gap-2">
										<Badge role="status" variant={priorityBadgeVariant(r.priority)}>
											{r.priority}
										</Badge>
										<Badge role="status" variant="secondary">
											{r.status}
										</Badge>
									</div>
								</div>
							))}
						</CardContent>
					</Card>
				</article>

				<article className="lg:col-span-3">
					<Card>
						<CardHeader>
							<div className="flex items-center justify-between gap-3">
								<CardTitle>Daily Drill</CardTitle>
								<Button variant="outline" size="sm">Answer</Button>
							</div>
							<CardDescription>One small improvement practice</CardDescription>
						</CardHeader>
						<CardContent className="flex items-center justify-between gap-3">
							<p className="text-sm text-muted-foreground">
								Run a 5-minute “5 Whys” on the top abnormality.
							</p>
							<div className="flex items-center gap-2">
								<Button asChild>
									<Link href="/training">Start Drill</Link>
								</Button>
							</div>
						</CardContent>
					</Card>
				</article>
			</div>
		</div>
	);
}
