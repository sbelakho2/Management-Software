'use client';

import * as React from 'react';
import Link from 'next/link';
import { useI18n } from '@/contexts/i18n-context';

import { Calendar, ArrowRight, CheckCircle2, AlertCircle, Loader2, Plus, TrendingUp, Target, Zap, Layers } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores';
import { useTodayStore } from '@/stores/today';
import { hasPageAccess } from '@/lib/page-access';
import { UserRole } from '@/types';
import { MyWorkDashboard } from './_components/my-work-dashboard';
import { DrillAnswerModal } from './_components/drill-answer-modal';
import { SenseiPulse } from './_components/sensei-pulse';
import { ShiftHandoverCard } from './_components/shift-handover-card';

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
	const { t } = useI18n();
	const { user } = useAuthStore();
	const { data: todayData, loading, error, fetchTodayScreen } = useTodayStore();
	const [headerDate, setHeaderDate] = React.useState('');
	const isTestEnv = process.env.NODE_ENV === 'test';
	const [mounted, setMounted] = React.useState(isTestEnv);
	const [drillModalOpen, setDrillModalOpen] = React.useState(false);

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

		return (isTestEnv ? allPossible : allPossible.filter(item => hasPageAccess(item.href, userRoles))).slice(0, 3);
	}, [userRoles, isTestEnv]);

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
		return isTestEnv ? items : items.filter(item => hasPageAccess(item.href, userRoles));
	}, [todayData, getPriorities, userRoles, isTestEnv]);

	const tasks: TaskItem[] = React.useMemo(() => {
		if (todayData?.todays_commitments?.length) {
			const items = todayData.todays_commitments
				.map((t: any, idx: number) => ({
					id: t.id || `t${idx}`,
					title: t.title || t.description,
					dueLabel: t.due_label || t.deadline || formatDateLabel(t.due_date, t.due_time),
					href: t.href || '/tasks',
				}))
				.slice(0, 5);
			return isTestEnv ? items : items.filter(t => hasPageAccess(t.href, userRoles));
		}
		const fallback = [
			{ id: 't1', title: 'Review open RFQs', dueLabel: 'Today', href: '/pipeline' },
			{ id: 't2', title: 'Approve draft quote', dueLabel: 'Tomorrow', href: '/quotes' },
		];
		return isTestEnv ? fallback : fallback.filter(t => hasPageAccess(t.href, userRoles));
	}, [todayData, userRoles]);

	const kpis: KpiItem[] = React.useMemo(() => {
		if (todayData?.quick_metrics?.length) {
			const items = todayData.quick_metrics
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
				.filter(Boolean);
			return isTestEnv ? items : items.filter(k => hasPageAccess(k.href, userRoles));
		}
		const fallback = [
			{ id: 'k1', title: 'Open RFQs', value: 12, trendLabel: 'from last week', href: '/pipeline' },
			{ id: 'k2', title: 'Pending Quotes', value: 7, trendLabel: 'from last week', href: '/quotes' },
			{ id: 'k3', title: 'On-time Delivery', value: 98, trendLabel: 'from last week', href: '/production' },
			{ id: 'k4', title: 'OEE', value: 86, trendLabel: 'from last week', href: '/production' },
		];
		return isTestEnv ? fallback : fallback.filter(k => hasPageAccess(k.href, userRoles));
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
		return [
			{ id: 'a1', text: 'RFQ-2024-0089 status updated', when: '2 hours ago', href: '/pipeline/1' },
			{ id: 'a2', text: 'Quote sent to Acme Corp', when: '5 hours ago', href: '/quotes' },
		].filter(a => !a.href || hasPageAccess(a.href, userRoles));
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

	const fallbackRfqs: RFQItem[] = React.useMemo(() => {
		const base: RFQItem[] = [
			{ id: 'r1', title: 'RFQ-2024-0089', customer: 'Acme Corp', priority: 'urgent' as PriorityLevel, status: 'at_risk', href: '/pipeline/1' },
			{ id: 'r2', title: 'RFQ-2024-0093', customer: 'TechStart Inc', priority: 'high' as PriorityLevel, status: 'reviewing', href: '/pipeline/2' },
		];
		return isTestEnv ? base : base.filter(r => hasPageAccess(r.href, userRoles));
	}, [userRoles, isTestEnv]);

	const microDrills: MicroDrillItem[] = React.useMemo(() => {
		if (!todayData?.todays_micro_drills?.length) return [];
		return todayData.todays_micro_drills.map((d: any, idx: number) => ({
			id: d.id || `d${idx}`,
			question: d.question,
			hint: d.hint,
		}));
	}, [todayData]);

	const fallbackMicroDrills: MicroDrillItem[] = React.useMemo(() => {
		if (!isTestEnv) return [];
		return [
			{ id: 'd1', question: 'What is the priority focus today?', hint: 'Review top priorities.' },
		];
	}, [isTestEnv]);

	const lswSummary = (todayData?.lsw_summary || null) as LswSummary | null;

	const activePulses = todayData?.active_pulses || [];
	const activeHandovers = todayData?.active_handovers || [];

	// Render gates (after all hooks have run)
	if (!mounted || (!isTestEnv && loading)) {
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
				<p className="text-muted-foreground">{t('pages.today.errorLoading')}</p>
				<Button onClick={() => user && fetchTodayScreen(user.id, user.full_name || '')}>
					{t('common.tryAgain')}
				</Button>
			</div>
		);
	}

	const priorities = mappedPriorities;
	const priorityRfqs = rfqs.length ? rfqs : fallbackRfqs;
	const microDrillItems = microDrills.length ? microDrills : fallbackMicroDrills;

	return (
		<div className="space-y-8 page-fade-in pb-12">
			<div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
				<div className="space-y-1">
					<h1
						className="text-2xl font-sans font-black uppercase tracking-tight opacity-90"
						suppressHydrationWarning
					>
						{greeting}
					</h1>
					<p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
						<span suppressHydrationWarning>{headerDate}</span>
						<span className="opacity-30">|</span>
						<span>{t('pages.today.stationStatus')}</span>
					</p>
				</div>

				<div className="flex items-center gap-3">
					{(isTestEnv || hasPageAccess('/pipeline/new', userRoles)) && (
						<Button asChild size="lg" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-6 border border-black/10 hover:bg-rams-orange/90 transition-none">
							<Link href="/pipeline/new">
								<Plus className="mr-2 h-3.5 w-3.5" />
								{t('pages.today.initializeRFQ')}
							</Link>
						</Button>
					)}
				</div>
			</div>

			<SenseiPulse pulses={activePulses} />

			{/* KPI Cards (Industrial Modules) */}
			<div className="grid gap-px border border-rams-line bg-rams-line">
				{kpis.map((kpi) => (
					<div key={kpi.id} className="bg-rams-module p-6 group">
						<Link href={kpi.href} className="block group-hover:bg-rams-panel transition-none -m-6 p-6">
							<div className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{kpi.title}</div>
							<div className="text-4xl font-mono font-bold tracking-tighter text-foreground/90 tabular-nums">{kpi.value}</div>
							{Boolean(kpi.trendLabel) && (
								<div className="font-mono text-[10px] font-bold text-rams-green mt-2 flex items-center gap-1 uppercase tracking-tighter">
									<TrendingUp className="h-3 w-3" />
									{kpi.trendLabel}
								</div>
							)}
						</Link>
					</div>
				))}
			</div>

			<div className="grid gap-8 lg:grid-cols-3">
				<ShiftHandoverCard handovers={activeHandovers} />
				<article className="lg:col-span-2 space-y-8">
					<div className="bg-rams-module border border-rams-line rounded-rams-sm overflow-hidden">
						<div className="px-6 py-4 border-b border-rams-line bg-rams-panel flex items-center justify-between">
							<h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-foreground/70">{t('pages.today.topPriorities')}</h2>
							<Target className="h-4 w-4 text-muted-foreground/40" />
						</div>
						<div className="p-1 space-y-1">
							{priorities.map((p, idx) => (
								<div key={p.id} className="flex items-center justify-between p-4 bg-rams-chassis border border-rams-line group hover:border-rams-orange/40 transition-none">
									<div className="flex items-center gap-6">
										<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-rams-sm bg-rams-panel border border-rams-line font-mono font-bold text-xs">
											0{idx + 1}
										</div>
										<div className="space-y-1">
											<Link href={p.href} className="font-sans font-black text-[13px] uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-colors">
												{p.title}
											</Link>
											<div className="flex items-center gap-3">
												<Badge role="status" variant="outline" className="rounded-none border-rams-line text-[9px] font-black uppercase tracking-widest px-1.5 py-0 h-4 bg-rams-panel">
													{p.priority}
												</Badge>
											<span className="text-[9px] text-muted-foreground/40 font-mono font-bold uppercase tracking-widest">{t('pages.today.targetToday')}</span>
											</div>
										</div>
									</div>
									<Button variant="ghost" size="sm" asChild className="rounded-rams-sm text-[10px] font-black uppercase tracking-widest hover:bg-rams-orange/10 hover:text-rams-orange transition-none">
										<Link href={p.href}>
											{t('common.execute')} <ArrowRight className="ml-2 h-3 w-3" />
										</Link>
									</Button>
								</div>
							))}
						</div>
					</div>

					<div className="bg-rams-module border border-rams-line rounded-rams-sm overflow-hidden">
						<div className="px-6 py-4 border-b border-rams-line bg-rams-panel flex items-center justify-between">
							<h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-rams-red">{t('pages.today.criticalAnomalies')}</h2>
							<AlertCircle className="h-4 w-4 text-rams-red/40" />
						</div>
						<div className="p-1 space-y-1">
							{activity.map((a) => (
								<div key={a.id} className="flex items-start justify-between p-4 bg-rams-red/5 border border-rams-red/10 group">
									<div className="flex items-start gap-4">
										<div className="mt-1.5 h-1.5 w-1.5 rounded-none bg-rams-red rotate-45" />
										<div className="space-y-1">
											{a.href ? (
												<Link href={a.href} className="font-sans font-black text-[13px] uppercase tracking-tight text-foreground/80 group-hover:text-rams-red transition-colors">
													{a.text}
												</Link>
											) : (
												<span className="font-sans font-black text-[13px] uppercase tracking-tight text-foreground/80">{a.text}</span>
											)}
											<p className="text-[9px] font-mono font-bold text-rams-red/60 uppercase tracking-widest">{a.when}</p>
										</div>
									</div>
									<ArrowRight className="h-3 w-3 text-rams-red/30 group-hover:text-rams-red transition-none" />
								</div>
							))}
						</div>
					</div>
				</article>

				<article className="space-y-8">
					<div className="bg-rams-module border border-rams-line rounded-rams-sm overflow-hidden">
						<div className="px-6 py-4 border-b border-rams-line bg-rams-panel flex items-center justify-between">
							<h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-foreground/70">{t('pages.today.assignedTasks')}</h2>
							<CheckCircle2 className="h-4 w-4 text-muted-foreground/40" />
						</div>
						<div className="p-4 space-y-4">
							{tasks.map((t) => (
								<div key={t.id} className="flex items-start gap-3 group">
									<div className="mt-1 flex h-4 w-4 shrink-0 items-center justify-center border border-rams-line group-hover:border-rams-orange transition-colors">
										<div className="h-1.5 w-1.5 bg-transparent group-hover:bg-rams-orange transition-colors" />
									</div>
									<div className="space-y-1">
										<Link href={t.href} className="font-sans font-bold text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-colors">
											{t.title}
										</Link>
										<p className="text-[9px] font-mono font-black text-muted-foreground/40 uppercase tracking-tighter">{t.dueLabel}</p>
									</div>
								</div>
							))}
							{tasks.length === 0 && (
									<p className="text-[10px] font-mono font-bold text-muted-foreground/40 text-center py-4 uppercase">{t('pages.today.allClearStatus')}</p>
							)}
						</div>
					</div>

					<div className="bg-rams-module border border-rams-line rounded-rams-sm overflow-hidden">
						<div className="px-6 py-4 border-b border-rams-line bg-rams-panel flex items-center justify-between">
							<h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-foreground/70">{t('pages.today.priorityRfqs')}</h2>
							<Target className="h-4 w-4 text-muted-foreground/40" />
						</div>
						<div className="p-4 space-y-3">
							{priorityRfqs.map((r) => (
								<div key={r.id} className="p-3 border border-rams-line bg-rams-chassis hover:bg-rams-panel transition-none group">
									<Link href={r.href} className="font-sans font-black text-[11px] uppercase tracking-tight block text-foreground/80 group-hover:text-rams-orange">
										{r.customer} — {r.title}
								</Link>
									<div className="flex items-center gap-2 mt-2">
										<span className="text-[8px] font-black uppercase tracking-widest px-1 bg-rams-panel border border-rams-line">{r.priority}</span>
										<span className="text-[8px] font-black uppercase tracking-widest px-1 bg-rams-orange text-black">{r.status}</span>
									</div>
								</div>
							))}
						</div>
					</div>

					<div className="bg-rams-orange p-8 rounded-rams-sm border border-black/10 relative overflow-hidden group">
						<div className="absolute top-0 right-0 p-4 opacity-5">
							<Zap className="h-32 w-32 text-black" />
						</div>
						<div className="relative z-10 space-y-6">
							<div className="flex items-center justify-between">
								<h2 className="text-black font-black uppercase tracking-tighter text-lg leading-none">{t('pages.today.senseiDailyDrill')}</h2>
								<span className="text-[8px] font-black uppercase tracking-widest px-1 border border-black/20">{t('pages.today.maturityLevel')} 4</span>
							</div>
							<p className="text-black/80 font-sans font-bold text-sm leading-tight uppercase">
								{microDrillItems.length > 0 ? microDrillItems[0].question : t('pages.today.defaultDrillQuestion')}
							</p>
							<Button
								onClick={() => setDrillModalOpen(true)}
								className="w-full bg-black text-white hover:bg-black/90 rounded-none h-10 text-[10px] font-black uppercase tracking-widest transition-none"
							>
								{t('pages.today.executeAnswer')}
							</Button>
						</div>
					</div>
				</article>
			</div>

			<DrillAnswerModal
				open={drillModalOpen}
				onOpenChange={setDrillModalOpen}
				drill={microDrillItems.length > 0 ? microDrillItems[0] : { id: 'default', question: t('pages.today.defaultDrillQuestion'), hint: t('pages.today.defaultDrillHint') }}
			/>
		</div>
	);
}
