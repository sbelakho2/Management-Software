'use client';

import * as React from 'react';
import Link from 'next/link';

import { Calendar, ArrowRight, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores';
import { useTodayStore } from '@/stores/today';

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
	const { data: todayData, loading, error, fetchTodayScreen } = useTodayStore();

	const firstName = user?.full_name?.split(' ')[0] || 'there';
	
	// Fetch data on mount
	React.useEffect(() => {
		if (user?.id && user?.full_name) {
			fetchTodayScreen(user.id, user.full_name);
		}
	}, [user?.id, user?.full_name, fetchTodayScreen]);

	// Convert API priorities to our format
	const mappedPriorities: PriorityItem[] = React.useMemo(() => {
		if (todayData?.top_priorities?.length) {
			return todayData.top_priorities.map((p: any, idx: number) => ({
				id: p.id || `p${idx}`,
				title: p.title || p.name,
				priority: (p.priority || 'medium') as PriorityLevel,
				href: p.href || p.link || '/pipeline',
			}));
		}
		// Fallback priorities if API returns empty
		return getPriorities();
	}, [todayData, user?.role]);

	const tasks: TaskItem[] = React.useMemo(() => {
		if (todayData?.todays_commitments?.length) {
			return todayData.todays_commitments.slice(0, 5).map((t: any, idx: number) => ({
				id: t.id || `t${idx}`,
				title: t.title || t.description,
				dueLabel: t.due_label || t.deadline || 'Today',
				href: t.href || '/tasks',
			}));
		}
		return [];
	}, [todayData]);

	const kpis: KpiItem[] = React.useMemo(() => {
		if (todayData?.quick_metrics?.length) {
			return todayData.quick_metrics.map((m: any, idx: number) => ({
				id: m.id || `k${idx}`,
				title: m.title || m.label,
				value: m.value ?? 0,
				trendLabel: m.trend_label || m.trend || '',
				href: m.href || '/analytics',
			}));
		}
		return [];
	}, [todayData]);

	// Show loading state
	if (loading) {
		return (
			<div className="flex items-center justify-center min-h-[400px]">
				<Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

	// Show error state
	if (error) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
				<AlertCircle className="h-12 w-12 text-destructive" />
				<p className="text-muted-foreground">Failed to load today&apos;s data</p>
				<Button onClick={() => user && fetchTodayScreen(user.id, user.full_name || '')}>
					Try Again
				</Button>
			</div>
		);
	}

	const getPriorities = (): PriorityItem[] => {
		const common = [
			{ id: 'p1', title: 'Close RFQ blockers for today', priority: 'urgent' as PriorityLevel, href: '/pipeline' },
		];

		if (user?.role === 'admin' || user?.role === 'ceo' || user?.role === 'gm' || user?.role === 'exec') {
			return [
				...common,
				{ id: 'p2', title: 'Review monthly strategic targets', priority: 'high' as PriorityLevel, href: '/executive' },
				{ id: 'p3', title: 'Analyze critical exceptions', priority: 'high' as PriorityLevel, href: '/exceptions' },
			];
		}

		if (user?.role === 'ops' || user?.role === 'supervisor') {
			return [
				...common,
				{ id: 'p2', title: 'Confirm production schedule risks', priority: 'high' as PriorityLevel, href: '/production' },
				{ id: 'p3', title: 'Review top quality abnormalities', priority: 'medium' as PriorityLevel, href: '/quality' },
			];
		}

		return common;
	};

	const priorities = getPriorities();

	const activity: ActivityItem[] = React.useMemo(() => {
		// Activity would come from todayData.recent_activity if available
		if (todayData?.abnormalities?.length) {
			return todayData.abnormalities.slice(0, 3).map((a: any, idx: number) => ({
				id: a.id || `a${idx}`,
				text: a.description || a.title,
				when: a.when || a.created_at || 'Recently',
				href: a.href || '/quality',
			}));
		}
		return [];
	}, [todayData]);

	const rfqs: RFQItem[] = React.useMemo(() => {
		// RFQs would come from todayData.top_risks.rfq if available
		if (todayData?.top_risks?.rfq?.length) {
			return todayData.top_risks.rfq.slice(0, 3).map((r: any, idx: number) => ({
				id: r.id || `r${idx}`,
				title: r.title || r.name,
				customer: r.customer || r.customer_name || 'Unknown',
				priority: (r.priority || 'medium') as PriorityLevel,
				status: r.status || 'new',
				href: r.href || `/pipeline/${r.id}`,
			}));
		}
		return [];
	}, [todayData]);

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
