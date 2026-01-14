'use client';

import * as React from 'react';
import Link from 'next/link';

import { Calendar, ArrowRight, CheckCircle2, AlertCircle, Loader2, Plus, TrendingUp, Target, Zap, Layers } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores';
import { useTodayStore } from '@/stores/today';
import { hasPageAccess } from '@/lib/page-access';
import { UserRole } from '@/types';
import { MyWorkDashboard } from './_components/my-work-dashboard';

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
	const [headerDate, setHeaderDate] = React.useState('');
	const [mounted, setMounted] = React.useState(false);

	const userRoles = React.useMemo(() => {
		if (!user) return [] as UserRole[];
		return user.roles?.length ? user.roles : [user.role as UserRole];
	}, [user]);

	const getPriorities = React.useCallback((): PriorityItem[] => {
		const allPossible = [
			{ id: 'p1', title: 'Close RFQ blockers for today', priority: 'urgent' as PriorityLevel, href: '/pipeline' },
			{ id: 'p2', title: 'Review monthly strategic targets', priority: 'high' as PriorityLevel, href: '/executive' },
			{ id: 'p3', title: 'Analyze critical exceptions', priority: 'high' as PriorityLevel, href: '/exceptions' },
			{ id: 'p4', title: 'Confirm production schedule risks', priority: 'high' as PriorityLevel, href: '/production' },
			{ id: 'p5', title: 'Review top quality abnormalities', priority: 'medium' as PriorityLevel, href: '/quality' },
		];

		return allPossible.filter(item => hasPageAccess(item.href, userRoles)).slice(0, 3);
	}, [userRoles]);

	const firstName = user?.full_name?.split(' ')[0] || 'there';

	React.useEffect(() => {
		setMounted(true);
		setHeaderDate(formatHeaderDate(new Date()));
	}, []);
	
	// Fetch data on mount
	React.useEffect(() => {
		if (user?.id && user?.full_name) {
			fetchTodayScreen(user.id, user.full_name);
		}
	}, [user?.id, user?.full_name, fetchTodayScreen]);

	// Convert API priorities to our format
	const mappedPriorities: PriorityItem[] = React.useMemo(() => {
		let items: PriorityItem[] = [];
		if (todayData?.top_priorities?.length) {
			items = todayData.top_priorities.map((p: any, idx: number) => ({
				id: p.id || `p${idx}`,
				title: p.title || p.name,
				priority: (p.priority || 'medium') as PriorityLevel,
				href: p.href || p.link || '/pipeline',
			}));
		} else {
			items = getPriorities();
		}
		return items.filter(item => hasPageAccess(item.href, userRoles));
	}, [todayData, getPriorities, userRoles]);

	const tasks: TaskItem[] = React.useMemo(() => {
		if (todayData?.todays_commitments?.length) {
			return todayData.todays_commitments
				.map((t: any, idx: number) => ({
					id: t.id || `t${idx}`,
					title: t.title || t.description,
					dueLabel: t.due_label || t.deadline || 'Today',
					href: t.href || '/tasks',
				}))
				.filter(t => hasPageAccess(t.href, userRoles))
				.slice(0, 5);
		}
		return [];
	}, [todayData, userRoles]);

	const kpis: KpiItem[] = React.useMemo(() => {
		if (todayData?.quick_metrics?.length) {
			return todayData.quick_metrics
				.map((m: any, idx: number) => ({
					id: m.id || `k${idx}`,
					title: m.title || m.label,
					value: m.value ?? 0,
					trendLabel: m.trend_label || m.trend || '',
					href: m.href || '/analytics',
				}))
				.filter(k => hasPageAccess(k.href, userRoles));
		}
		return [];
	}, [todayData, userRoles]);

	const activity: ActivityItem[] = React.useMemo(() => {
		// Activity would come from todayData.recent_activity if available
		if (todayData?.abnormalities?.length) {
			return todayData.abnormalities
				.map((a: any, idx: number) => ({
					id: a.id || `a${idx}`,
					text: a.description || a.title,
					when: a.when || a.created_at || 'Recently',
					href: a.href || '/quality',
				}))
				.filter(a => !a.href || hasPageAccess(a.href, userRoles))
				.slice(0, 3);
		}
		return [];
	}, [todayData, userRoles]);

	const rfqs: RFQItem[] = React.useMemo(() => {
		// RFQs would come from todayData.top_risks.rfq if available
		if (todayData?.top_risks?.rfq?.length) {
			return todayData.top_risks.rfq
				.map((r: any, idx: number) => ({
					id: r.id || `r${idx}`,
					title: r.title || r.name,
					customer: r.customer || r.customer_name || 'Unknown',
					priority: (r.priority || 'medium') as PriorityLevel,
					status: r.status || 'new',
					href: r.href || `/pipeline/${r.id}`,
				}))
				.filter(r => hasPageAccess(r.href, userRoles))
				.slice(0, 3);
		}
		return [];
	}, [todayData, userRoles]);

	// Render gates (after all hooks have run)
	if (!mounted || loading) {
		return (
			<div className="flex items-center justify-center min-h-[400px]">
				<Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

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

	const priorities = mappedPriorities;

	return (
		<div className="space-y-8 page-fade-in">
			<div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
				<div className="space-y-1">
					<h1
						className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70"
						suppressHydrationWarning
					>
						Hello, {firstName}!
					</h1>
					<p className="text-muted-foreground font-medium flex items-center gap-2">
						<Calendar className="h-4 w-4 text-primary" />
						<span suppressHydrationWarning>{headerDate}</span> • Intelligence Command Center
					</p>
				</div>

				<div className="flex items-center gap-3">
					{hasPageAccess('/pipeline/new', userRoles) && (
						<Button asChild size="lg" className="rounded-xl shadow-glow subtle-shine">
							<Link href="/pipeline/new">
								<Plus className="mr-2 h-4 w-4" />
								Create RFQ
							</Link>
						</Button>
					)}
				</div>
			</div>

			{/* KPI Cards */}
			<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
				{kpis.map((kpi) => (
					<Card key={kpi.id} className="group">
						<CardHeader className="space-y-1">
							<Link href={kpi.href} className="block group-hover:translate-x-1 transition-transform">
								<CardTitle className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">{kpi.title}</CardTitle>
								<div className="text-3xl font-bold mt-1 tracking-tight">{kpi.value}</div>
								<CardDescription className="font-medium text-success/80 mt-1 flex items-center gap-1">
									<TrendingUp className="h-3 w-3" />
									{kpi.trendLabel}
								</CardDescription>
							</Link>
						</CardHeader>
					</Card>
				))}
			</div>

			<div className="grid gap-8 lg:grid-cols-3">
				<article className="lg:col-span-2">
					<Card className="h-full">
						<CardHeader>
							<div className="flex items-center justify-between">
								<div>
									<CardTitle className="text-xl">Top Priorities</CardTitle>
									<CardDescription>Strategic focus items for today</CardDescription>
								</div>
								<Target className="h-5 w-5 text-primary/40" />
							</div>
						</CardHeader>
						<CardContent className="space-y-4">
							{priorities.map((p, idx) => (
								<div key={p.id} className="flex items-center justify-between p-4 rounded-xl bg-muted/30 border border-border/10 hover:bg-muted/50 transition-colors group">
									<div className="flex items-center gap-4">
										<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-background border font-bold shadow-sm">
											{idx + 1}
										</div>
										<div className="space-y-1">
											<Link href={p.href} className="font-bold text-foreground/90 group-hover:text-primary transition-colors">
												{p.title}
											</Link>
											<div className="flex items-center gap-2">
												<Badge role="status" variant={priorityBadgeVariant(p.priority)} className="rounded-md text-[10px] font-bold uppercase tracking-wider">
													{p.priority}
												</Badge>
												<span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">Target Today</span>
											</div>
										</div>
									</div>
									<Button variant="ghost" size="sm" asChild className="rounded-lg group-hover:bg-primary/10 group-hover:text-primary transition-all">
										<Link href={p.href}>
											Execute <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
										</Link>
									</Button>
								</div>
							))}
						</CardContent>
					</Card>
				</article>

				<article>
					<div className="space-y-8">
						<Card>
							<CardHeader>
								<div className="flex items-center justify-between">
									<div>
										<CardTitle className="text-xl">My Tasks</CardTitle>
										<CardDescription>Assigned commitments</CardDescription>
									</div>
									<CheckCircle2 className="h-5 w-5 text-primary/40" />
								</div>
							</CardHeader>
							<CardContent className="space-y-4">
								{tasks.map((t) => (
									<div key={t.id} className="flex items-start gap-4 p-2 rounded-lg hover:bg-muted/50 transition-colors group">
										<div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-muted-foreground/30 group-hover:border-primary/50 transition-colors">
											<div className="h-2 w-2 rounded-full bg-transparent group-hover:bg-primary transition-all" />
										</div>
										<div className="space-y-1">
											<Link href={t.href} className="font-bold text-sm text-foreground/80 hover:text-primary transition-colors">
												{t.title}
											</Link>
											<p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">{t.dueLabel}</p>
										</div>
									</div>
								))}
								{tasks.length === 0 && (
									<p className="text-sm text-muted-foreground py-4 text-center italic">All clear for today</p>
								)}
								{hasPageAccess('/tasks', userRoles) && (
									<div className="pt-2">
										<Button variant="ghost" size="sm" asChild className="w-full justify-between text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-xl">
											<Link href="/tasks" className="flex items-center w-full justify-between">
												<span className="text-xs font-bold uppercase tracking-widest">View All Tasks</span>
												<ArrowRight className="h-4 w-4" />
											</Link>
										</Button>
									</div>
								)}
							</CardContent>
						</Card>

						<Card>
							<CardHeader>
								<div className="flex items-center justify-between">
									<div>
										<CardTitle className="text-xl">Project Work</CardTitle>
										<CardDescription>Stories and Issues</CardDescription>
									</div>
									<Layers className="h-5 w-5 text-primary/40" />
								</div>
							</CardHeader>
							<CardContent>
								<MyWorkDashboard />
							</CardContent>
						</Card>
					</div>
				</article>

				<article className="lg:col-span-2">
					<Card>
						<CardHeader>
							<div className="flex items-center justify-between">
								<div>
									<CardTitle className="text-xl text-danger flex items-center gap-2">
										<AlertCircle className="h-5 w-5" />
										Anomalies & Activity
									</CardTitle>
									<CardDescription>Real-time factory floor updates</CardDescription>
								</div>
							</div>
						</CardHeader>
						<CardContent className="space-y-4">
							{activity.map((a) => (
								<div key={a.id} className="flex items-start justify-between p-3 rounded-xl bg-danger/5 border border-danger/10 hover:bg-danger/10 transition-colors group">
									<div className="flex items-start gap-3">
										<div className="mt-1 h-2 w-2 rounded-full bg-danger animate-pulse" />
										<div className="space-y-1">
											{a.href ? (
												<Link href={a.href} className="font-bold text-sm hover:underline decoration-danger/30 underline-offset-4">
													{a.text}
												</Link>
											) : (
												<span className="font-bold text-sm">{a.text}</span>
											)}
											<p className="text-[10px] uppercase tracking-widest font-bold text-danger/60">{a.when}</p>
										</div>
									</div>
									<ArrowRight className="h-4 w-4 text-danger/40 group-hover:translate-x-1 transition-transform" />
								</div>
							))}
							{activity.length === 0 && (
								<div className="py-8 text-center space-y-2">
									<CheckCircle2 className="h-8 w-8 text-success mx-auto" />
									<p className="text-sm font-medium text-muted-foreground">System stable. No active anomalies.</p>
								</div>
							)}
						</CardContent>
					</Card>
				</article>

				<article>
					<Card>
						<CardHeader className="flex flex-row items-center justify-between space-y-0">
							<div>
								<CardTitle className="text-xl">Priority RFQs</CardTitle>
								<CardDescription>Sales pipeline high-focus</CardDescription>
							</div>
							<Target className="h-5 w-5 text-primary/40" />
						</CardHeader>
						<CardContent className="space-y-4">
							{rfqs.map((r) => (
								<div key={r.id} className="space-y-2 p-3 rounded-xl hover:bg-muted/50 transition-colors group">
									<Link href={r.href} className="font-bold text-sm block group-hover:text-primary transition-colors">
										{r.customer} • {r.title}
									</Link>
									<div className="flex items-center gap-2">
										<Badge role="status" variant={priorityBadgeVariant(r.priority)} className="text-[10px] font-bold uppercase tracking-widest rounded-md px-1.5 py-0">
											{r.priority}
										</Badge>
										<Badge role="status" variant="secondary" className="text-[10px] font-bold uppercase tracking-widest rounded-md px-1.5 py-0 bg-primary/5 text-primary border-primary/10">
											{r.status}
										</Badge>
									</div>
								</div>
							))}
							{rfqs.length === 0 && (
								<p className="text-sm text-muted-foreground py-4 text-center italic">No priority RFQs</p>
							)}
							{hasPageAccess('/pipeline', userRoles) && (
								<Button variant="ghost" size="sm" asChild className="w-full justify-between text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-xl">
									<Link href="/pipeline" className="flex items-center w-full justify-between">
										<span className="text-xs font-bold uppercase tracking-widest">Open Pipeline</span>
										<ArrowRight className="h-4 w-4" />
									</Link>
								</Button>
							)}
						</CardContent>
					</Card>
				</article>

				<article className="lg:col-span-3">
					<Card className="bg-primary shadow-lg shadow-primary/20 border-none overflow-hidden relative group">
						<div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform duration-700">
							<Target className="h-32 w-32 text-white" />
						</div>
						<CardHeader>
							<div className="flex items-center justify-between relative z-10">
								<CardTitle className="text-white text-xl flex items-center gap-2">
									<Zap className="h-5 w-5 fill-white" />
									Sensei Daily Drill
								</CardTitle>
								<Badge className="bg-white/20 text-white border-white/20 hover:bg-white/30 backdrop-blur-md">
									Level 4 Maturity
								</Badge>
							</div>
							<CardDescription className="text-primary-foreground/70 font-medium">Precision improvement practice</CardDescription>
						</CardHeader>
						<CardContent className="flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
							<p className="text-white font-medium text-lg">
								"Run a 5-minute “5 Whys” on the top abnormality to identify root causes before they cascade."
							</p>
							<div className="flex items-center gap-3 shrink-0">
								{hasPageAccess('/training', userRoles) && (
									<Button asChild variant="secondary" className="bg-white text-primary hover:bg-white/90 shadow-xl rounded-xl font-bold">
										<Link href="/training">Execute Drill</Link>
									</Button>
								)}
							</div>
						</CardContent>
					</Card>
				</article>
			</div>
		</div>
	);
}
