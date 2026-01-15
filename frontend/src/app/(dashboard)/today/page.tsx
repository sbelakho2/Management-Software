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

type MicroDrillItem = {
	id: string;
	question: string;
	hint?: string;
};

type LswSummary = {
	daily_status: string;
	daily_total: number;
	daily_completed: number;
	weekly_status: string;
	weekly_total: number;
	weekly_completed: number;
	monthly_status: string;
	monthly_total: number;
	monthly_completed: number;
	overdue_count: number;
	next_due_item?: string | null;
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

function severityToPriority(severity?: number): PriorityLevel {
	if (!severity) return 'medium';
	if (severity >= 9) return 'urgent';
	if (severity >= 7) return 'high';
	if (severity <= 3) return 'low';
	return 'medium';
}

function formatDateLabel(rawDate?: string, rawTime?: string): string {
	if (!rawDate) return 'Today';
	const parsed = new Date(rawDate);
	if (Number.isNaN(parsed.getTime())) return 'Today';
	const dateLabel = parsed.toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
	});
	return rawTime ? `${dateLabel} ${rawTime}` : dateLabel;
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
	const greeting = todayData?.greeting || `Hello, ${firstName}!`;

	React.useEffect(() => {
		setMounted(true);
		setHeaderDate(formatHeaderDate(new Date()));
	}, []);

	React.useEffect(() => {
		if (todayData?.current_date) {
			const parsed = new Date(todayData.current_date);
			if (!Number.isNaN(parsed.getTime())) {
				setHeaderDate(formatHeaderDate(parsed));
			}
		}
	}, [todayData?.current_date]);
	
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
				priority: (p.priority_level || p.priority || 'medium') as PriorityLevel,
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
					dueLabel: t.due_label || t.deadline || formatDateLabel(t.due_date, t.due_time),
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
				.map((m: any, idx: number) => {
					const trendValue = m.trend_value ?? m.trendValue;
					const trendText = trendValue !== undefined && trendValue !== null
						? `${m.trend === 'down' ? '' : '+'}${trendValue}`
						: '';
					const trendLabel = m.trend_label || m.trend || trendText;
					return {
						id: m.id || `k${idx}`,
						title: m.title || m.label || m.name,
						value: m.value ?? 0,
						trendLabel,
						href: m.href || m.link || '/analytics',
					};
				})
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
					when: a.when || a.detected_at || a.created_at || 'Recently',
					href: a.href || '/quality',
				}))
				.filter(a => !a.href || hasPageAccess(a.href, userRoles))
				.slice(0, 3);
		}
		return [];
	}, [todayData, userRoles]);

	const rfqs: RFQItem[] = React.useMemo(() => {
		const risks = todayData?.top_risks
			? Object.values(todayData.top_risks).flat()
			: [];
		const explicitRfqs = todayData?.top_risks?.rfq || [];
		const rfqRisks = [...explicitRfqs, ...risks].filter(
			(r: any) => (r?.entity_type || '').toLowerCase() === 'rfq'
		);
		if (!rfqRisks.length) return [];
		return rfqRisks
			.map((r: any, idx: number) => ({
				id: r.id || `r${idx}`,
				title: r.title || r.name || r.description || 'RFQ at risk',
				customer: r.customer || r.customer_name || r.owner_name || 'Unknown',
				priority: severityToPriority(r.severity),
				status: r.status || 'at_risk',
				href: r.href || (r.entity_id ? `/pipeline/${r.entity_id}` : '/pipeline'),
			}))
			.filter(r => hasPageAccess(r.href, userRoles))
			.slice(0, 3);
	}, [todayData, userRoles]);

	const microDrills: MicroDrillItem[] = React.useMemo(() => {
		if (!todayData?.todays_micro_drills?.length) return [];
		return todayData.todays_micro_drills.map((d: any, idx: number) => ({
			id: d.id || `d${idx}`,
			question: d.question,
			hint: d.hint,
		}));
	}, [todayData]);

	const lswSummary = (todayData?.lsw_summary || null) as LswSummary | null;

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
						className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70"
						suppressHydrationWarning
					>
						{greeting}
					</h1>
					<p className="text-sm text-muted-foreground font-medium flex items-center gap-2">
						<Calendar className="h-4 w-4 text-primary/60" />
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
								<div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{kpi.value}</div>
								{Boolean(kpi.trendLabel) && (
									<CardDescription className="font-medium text-success/80 mt-1 flex items-center gap-1">
										<TrendingUp className="h-3 w-3" />
										{kpi.trendLabel}
									</CardDescription>
								)}
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
								<div key={p.id} className="flex items-center justify-between p-5 rounded-[1.5rem] bg-muted/20 border border-border/5 hover:bg-primary/5 hover:border-primary/10 transition-all duration-300 group">
									<div className="flex items-center gap-5">
										<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-background border border-border/10 font-heading font-bold text-lg shadow-sm group-hover:scale-110 transition-transform duration-500">
											{idx + 1}
										</div>
										<div className="space-y-1.5">
											<Link href={p.href} className="font-heading font-bold text-base tracking-tight text-foreground/80 group-hover:text-primary transition-colors">
												{p.title}
											</Link>
											<div className="flex items-center gap-3">
												<Badge role="status" variant={priorityBadgeVariant(p.priority)} className="rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest">
													{p.priority}
												</Badge>
												<span className="text-[9px] text-muted-foreground/60 font-bold uppercase tracking-[0.2em]">Target Today</span>
											</div>
										</div>
									</div>
									<Button variant="ghost" size="sm" asChild className="rounded-xl group-hover:bg-primary/10 group-hover:text-primary transition-all">
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
									<div key={t.id} className="flex items-start gap-4 p-3 rounded-2xl bg-muted/10 border border-border/5 hover:bg-primary/5 hover:border-primary/10 transition-all duration-300 group">
										<div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-muted-foreground/20 group-hover:border-primary/40 transition-colors">
											<div className="h-2 w-2 rounded-full bg-transparent group-hover:bg-primary group-hover:shadow-glow transition-all" />
										</div>
										<div className="space-y-1">
											<Link href={t.href} className="font-heading font-bold text-sm tracking-tight text-foreground/80 group-hover:text-primary transition-colors">
												{t.title}
											</Link>
											<p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40">{t.dueLabel}</p>
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

						{lswSummary && (
							<Card>
								<CardHeader>
									<div className="flex items-center justify-between">
										<div>
											<CardTitle className="text-xl">Leader Standard Work</CardTitle>
											<CardDescription>Checklist completion</CardDescription>
										</div>
										<Target className="h-5 w-5 text-primary/40" />
									</div>
								</CardHeader>
								<CardContent className="space-y-3">
									<div className="text-sm text-muted-foreground">
										Daily: <span className="font-semibold text-foreground">{lswSummary.daily_completed}/{lswSummary.daily_total}</span>
									</div>
									<div className="text-sm text-muted-foreground">
										Weekly: <span className="font-semibold text-foreground">{lswSummary.weekly_completed}/{lswSummary.weekly_total}</span>
									</div>
									<div className="text-sm text-muted-foreground">
										Monthly: <span className="font-semibold text-foreground">{lswSummary.monthly_completed}/{lswSummary.monthly_total}</span>
									</div>
									{lswSummary.overdue_count > 0 && (
										<Badge role="status" variant="destructive" className="w-fit">Overdue: {lswSummary.overdue_count}</Badge>
									)}
									{lswSummary.next_due_item && (
										<p className="text-xs text-muted-foreground">Next due: {lswSummary.next_due_item}</p>
									)}
								</CardContent>
							</Card>
						)}
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
								<div key={a.id} className="flex items-start justify-between p-4 rounded-[1.5rem] bg-danger/5 border border-danger/5 hover:bg-danger/10 transition-all duration-300 group">
									<div className="flex items-start gap-4">
										<div className="mt-1.5 h-2 w-2 rounded-full bg-danger animate-pulse shadow-[0_0_8px_rgba(220,38,38,0.5)]" />
										<div className="space-y-1">
											{a.href ? (
												<Link href={a.href} className="font-heading font-bold text-sm tracking-tight text-foreground/80 group-hover:text-danger transition-colors">
													{a.text}
												</Link>
											) : (
												<span className="font-heading font-bold text-sm tracking-tight text-foreground/80">{a.text}</span>
											)}
											<p className="text-[9px] uppercase tracking-[0.2em] font-bold text-danger/40">{a.when}</p>
										</div>
									</div>
									<ArrowRight className="h-4 w-4 text-danger/30 group-hover:translate-x-1 transition-transform" />
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
								<div key={r.id} className="space-y-2.5 p-4 rounded-[1.5rem] bg-muted/10 border border-border/5 hover:bg-primary/5 hover:border-primary/10 transition-all duration-300 group">
									<Link href={r.href} className="font-heading font-bold text-sm tracking-tight block text-foreground/80 group-hover:text-primary transition-colors">
										{r.customer} • {r.title}
									</Link>
									<div className="flex items-center gap-2">
										<Badge role="status" variant={priorityBadgeVariant(r.priority)} className="text-[9px] font-bold uppercase tracking-widest rounded-md px-1.5 py-0 bg-background/50">
											{r.priority}
										</Badge>
										<Badge role="status" variant="secondary" className="text-[9px] font-bold uppercase tracking-widest rounded-md px-1.5 py-0 bg-primary/5 text-primary border-primary/10">
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
					<Card className="bg-primary shadow-glow shadow-primary/20 border-none overflow-hidden relative group rounded-[3rem]">
						<div className="absolute top-0 right-0 p-12 opacity-10 group-hover:scale-110 transition-transform duration-1000 ease-out">
							<Target className="h-48 w-48 text-white" />
						</div>
						<div className="absolute inset-0 bg-gradient-to-br from-primary to-primary/80" />
						<div className="absolute inset-0 opacity-[0.15] mix-blend-soft-light" 
							 style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
						/>
						<CardHeader className="relative z-10 p-10 pb-6">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-4">
									<div className="p-3 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 shadow-lg">
										<Zap className="h-6 w-6 text-white fill-white animate-pulse" />
									</div>
									<CardTitle className="text-white text-2xl font-heading tracking-tight">Sensei Daily Drill</CardTitle>
								</div>
								<Badge className="bg-white/20 text-white border-white/20 hover:bg-white/30 backdrop-blur-md rounded-lg px-3 py-1 font-black uppercase tracking-widest text-[9px]">
									LEVEL 4 MATURITY
								</Badge>
							</div>
							<CardDescription className="text-white/60 font-bold uppercase tracking-[0.2em] mt-4 ml-1">Continuous Improvement Practice established</CardDescription>
						</CardHeader>
						<CardContent className="relative z-10 p-10 pt-0 flex flex-col md:flex-row items-center justify-between gap-10">
							{microDrills.length > 0 ? (
								<div className="space-y-3 flex-1">
									<p className="text-white font-heading font-bold text-xl leading-relaxed tracking-tight">{microDrills[0].question}</p>
									{microDrills[0].hint && (
										<div className="flex items-center gap-2 text-white/50">
											<div className="h-1 w-1 rounded-full bg-white/30" />
											<p className="text-xs font-medium italic">Sensei Intelligence: {microDrills[0].hint}</p>
										</div>
									)}
								</div>
							) : (
								<p className="text-white font-heading font-bold text-xl leading-relaxed tracking-tight flex-1">
									"Run a 5-minute “5 Whys” on the top organizational abnormality to identify root causes before they cascade."
								</p>
							)}
							<div className="flex items-center gap-4 shrink-0">
								{hasPageAccess('/training', userRoles) && (
									<Button asChild variant="secondary" className="bg-white text-primary hover:bg-white/95 shadow-xl rounded-[1.25rem] font-black uppercase tracking-widest h-14 px-10 active:scale-95 transition-all text-xs">
										<Link href="/training">Execute Protocol</Link>
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
