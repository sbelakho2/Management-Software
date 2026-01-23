import * as React from 'react';
import { Zap, AlertTriangle, Info } from 'lucide-react';
import { GlobalPulseSummary } from '@/api/today';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface SenseiPulseProps {
	pulses: GlobalPulseSummary[];
}

export function SenseiPulse({ pulses }: SenseiPulseProps) {
	if (!pulses || pulses.length === 0) return null;

	return (
		<div className="space-y-1 mb-8">
			{pulses.map((pulse) => (
				<div
					key={pulse.id}
					className={cn(
						"relative overflow-hidden rounded-rams-sm border px-6 py-4 flex items-center gap-6 transition-all animate-in fade-in slide-in-from-top-4 duration-500",
						pulse.severity === 'critical'
							? "bg-rams-red border-black/10 text-white"
							: pulse.severity === 'warning'
								? "bg-rams-orange border-black/10 text-black"
								: "bg-rams-module border-rams-line text-foreground/80"
					)}
				>
					<div className="flex-shrink-0">
						{pulse.severity === 'critical' ? (
							<AlertTriangle className="h-6 w-6" />
						) : pulse.severity === 'warning' ? (
							<Zap className="h-6 w-6" />
						) : (
							<Info className="h-6 w-6" />
						)}
					</div>

					<div className="flex-grow">
						<div className="flex items-center gap-3 mb-1">
							<span className={cn(
								"font-black uppercase text-[10px] tracking-[0.2em]",
								pulse.severity === 'critical' ? "text-white/70" : "text-black/50"
							)}>
								Sensei Pulse
							</span>
							{pulse.highlight_metric_name && (
								<Badge variant="outline" className={cn(
									"rounded-none border-current font-mono text-[9px] font-black uppercase px-1.5 py-0 h-4",
									pulse.severity === 'critical' ? "bg-white/10 text-white" : "bg-black/5 text-black"
								)}>
									{pulse.highlight_metric_name}: {pulse.highlight_metric_value}
								</Badge>
							)}
						</div>
						<p className="text-sm font-sans font-bold leading-none uppercase tracking-tight">
							{pulse.message}
						</p>
					</div>

					{pulse.severity === 'critical' && (
						<div className="absolute top-0 right-0 p-2 opacity-10">
							<AlertTriangle className="h-16 w-16 -mr-4 -mt-4 rotate-12" />
						</div>
					)}
				</div>
			))}
		</div>
	);
}
