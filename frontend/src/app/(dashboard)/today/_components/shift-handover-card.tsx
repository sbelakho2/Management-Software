'use client';

import * as React from 'react';
import { ClipboardList, Shield, CheckCircle2, Truck, MessageSquare, Check, Loader2 } from 'lucide-react';
import { HandoverNoteSummary } from '@/api/today';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { productionApi } from '@/api/production';
import { useTodayStore } from '@/stores/today';
import { useAuthStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';

interface ShiftHandoverCardProps {
	handovers: HandoverNoteSummary[];
}

export function ShiftHandoverCard({ handovers }: ShiftHandoverCardProps) {
	const { t, formatDate } = useI18n();
	const { user } = useAuthStore();
	const { fetchTodayScreen } = useTodayStore();
	const [acknowledgingId, setAcknowledgingId] = React.useState<number | null>(null);

	const displayName = React.useMemo(() => {
		if (!user) return t('pages.today.greetingFallback');
		const fullName = (user.full_name || '').trim();
		if (fullName) return fullName;
		const email = (user.email || '').trim();
		if (email) return email;
		return t('pages.today.greetingFallback');
	}, [user, t]);

	const handleAcknowledge = async (id: number) => {
		setAcknowledgingId(id);
		try {
			await productionApi.acknowledgeHandover(id);
			if (user?.id) {
				fetchTodayScreen(user.id, displayName);
			}
		} catch (error) {
			console.error('Failed to acknowledge handover:', error);
		} finally {
			setAcknowledgingId(null);
		}
	};

	if (!handovers || handovers.length === 0) return null;

	return (
		<div className="bg-rams-module border border-rams-line rounded-rams-sm overflow-hidden h-full flex flex-col">
			<div className="px-6 py-4 border-b border-rams-line bg-rams-panel flex items-center justify-between">
				<h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-foreground/70">{t('pages.today.handover.title')}</h2>
				<div className="flex items-center gap-3">
					<Badge variant="outline" className="rounded-none border-rams-line text-[9px] font-black uppercase tracking-widest px-1.5 py-0 h-4 bg-rams-panel">
						{handovers.length} {handovers.length === 1 ? t('pages.today.handover.note') : t('pages.today.handover.notes')}
					</Badge>
					<ClipboardList className="h-4 w-4 text-muted-foreground/40" />
				</div>
			</div>

			<div className="flex-grow p-1 space-y-1 overflow-y-auto">
				{handovers.map((note) => (
					<div key={note.id} className="bg-rams-chassis border border-rams-line p-4 space-y-4 hover:border-rams-orange/40 transition-none group/item">
						<div className="flex justify-between items-start">
							<div className="space-y-1">
								<div className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
									{t('pages.today.handover.station', { id: note.station_id })}
								</div>
								<div className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase">
									{formatDate(note.created_at, { timeStyle: 'short' })}
								</div>
							</div>
							<Badge
								className={cn(
									"rounded-none text-[8px] font-black uppercase tracking-widest px-1 py-0 h-4 transition-none",
									note.severity === 'critical' ? "bg-rams-red text-white" :
										note.severity === 'warning' ? "bg-rams-orange text-black" :
											"bg-rams-panel text-foreground/60 border border-rams-line"
								)}
							>
								{t(`pages.today.severity.${note.severity}`)}
							</Badge>
						</div>

						<div className="grid grid-cols-1 gap-3">
							{note.safety && (
								<div className="flex gap-3 items-start">
									<div className="mt-1 h-1.5 w-1.5 rounded-none bg-rams-red flex-shrink-0" />
									<div>
										<span className="text-[9px] font-black uppercase tracking-widest text-rams-red/80">{t('pages.today.handover.safety')}</span>
										<p className="text-[11px] font-sans font-bold uppercase tracking-tight text-foreground/80 leading-tight">{note.safety}</p>
									</div>
								</div>
							)}
							{note.quality && (
								<div className="flex gap-3 items-start">
									<div className="mt-1 h-1.5 w-1.5 rounded-none bg-rams-green flex-shrink-0" />
									<div>
										<span className="text-[9px] font-black uppercase tracking-widest text-rams-green/80">{t('pages.today.handover.quality')}</span>
										<p className="text-[11px] font-sans font-bold uppercase tracking-tight text-foreground/80 leading-tight">{note.quality}</p>
									</div>
								</div>
							)}
							{note.delivery && (
								<div className="flex gap-3 items-start">
									<div className="mt-1 h-1.5 w-1.5 rounded-none bg-rams-steel flex-shrink-0" />
									<div>
										<span className="text-[9px] font-black uppercase tracking-widest text-rams-steel/80">{t('pages.today.handover.delivery')}</span>
										<p className="text-[11px] font-sans font-bold uppercase tracking-tight text-foreground/80 leading-tight">{note.delivery}</p>
									</div>
								</div>
							)}
							{note.notes && (
								<div className="mt-1 pt-3 border-t border-rams-line/50">
									<div className="flex gap-3 items-start">
										<MessageSquare className="h-3 w-3 text-muted-foreground/30 mt-0.5 flex-shrink-0" />
										<p className="text-[10px] font-mono font-medium text-muted-foreground/70 leading-relaxed uppercase">{note.notes}</p>
									</div>
								</div>
							)}
						</div>

						<div className="pt-2">
							<Button
								onClick={() => handleAcknowledge(note.id)}
								disabled={acknowledgingId === note.id}
								variant="outline"
								size="sm"
								className="w-full rounded-none border-rams-line bg-rams-panel text-[9px] font-black uppercase tracking-widest h-8 hover:bg-rams-green hover:text-white hover:border-transparent transition-all"
							>
								{acknowledgingId === note.id ? (
									<Loader2 className="h-3 w-3 animate-spin mr-2" />
								) : (
									<Check className="h-3 w-3 mr-2" />
								)}
								{t('pages.today.handover.acknowledge')}
							</Button>
						</div>
					</div>
				))}
			</div>
		</div>
	);
}
