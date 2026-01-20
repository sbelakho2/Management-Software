'use client';

import * as React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface GRRResult {
  repeatability_ev: number;
  reproducibility_av: number;
  grr: number;
  part_variation_pv: number;
  total_variation_tv: number;
  grr_percent: number;
  ndc: number;
}

interface GRRResultsChartProps {
  result: GRRResult;
  gaugeName?: string;
  studyName?: string;
  className?: string;
}

// AIAG Guidelines for GRR acceptability
const GRR_THRESHOLDS = {
  EXCELLENT: 10,  // < 10% is excellent
  ACCEPTABLE: 30, // 10-30% is acceptable
  // > 30% is unacceptable
};

const NDC_THRESHOLD = 5; // Minimum 5 distinct categories per AIAG

function getGRRStatus(grrPercent: number): { status: 'excellent' | 'acceptable' | 'unacceptable'; color: string; label: string } {
  if (grrPercent < GRR_THRESHOLDS.EXCELLENT) {
    return { status: 'excellent', color: 'text-green-600', label: 'Excellent' };
  } else if (grrPercent < GRR_THRESHOLDS.ACCEPTABLE) {
    return { status: 'acceptable', color: 'text-yellow-600', label: 'Acceptable' };
  }
  return { status: 'unacceptable', color: 'text-red-600', label: 'Unacceptable' };
}

function getNDCStatus(ndc: number): { isAcceptable: boolean; color: string } {
  return {
    isAcceptable: ndc >= NDC_THRESHOLD,
    color: ndc >= NDC_THRESHOLD ? 'text-green-600' : 'text-red-600',
  };
}

export function GRRResultsChart({ result, gaugeName, studyName, className }: GRRResultsChartProps) {
  const grrStatus = getGRRStatus(result.grr_percent);
  const ndcStatus = getNDCStatus(result.ndc);

  // Calculate percentages for the stacked bar
  const evPercent = (result.repeatability_ev / result.total_variation_tv) * 100;
  const avPercent = (result.reproducibility_av / result.total_variation_tv) * 100;
  const pvPercent = (result.part_variation_pv / result.total_variation_tv) * 100;

  return (
    <Card className={cn('rounded-rams-sm border-rams-line', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-heading">GRR Analysis Results</CardTitle>
            {(gaugeName || studyName) && (
              <CardDescription className="text-xs">
                {studyName && <span>{studyName}</span>}
                {studyName && gaugeName && <span> • </span>}
                {gaugeName && <span>Gauge: {gaugeName}</span>}
              </CardDescription>
            )}
          </div>
          <Badge
            variant={grrStatus.status === 'excellent' ? 'default' : grrStatus.status === 'acceptable' ? 'secondary' : 'destructive'}
            className="text-xs font-bold"
          >
            {grrStatus.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main GRR Percentage Indicator */}
        <div className="text-center space-y-2">
          <div className="text-5xl font-bold tabular-nums">
            <span className={grrStatus.color}>{result.grr_percent.toFixed(1)}</span>
            <span className="text-2xl text-muted-foreground">%</span>
          </div>
          <p className="text-sm text-muted-foreground">Total Gage R&R</p>
          <div className="flex items-center justify-center gap-1 text-xs">
            {grrStatus.status === 'excellent' && <CheckCircle className="h-3 w-3 text-green-600" />}
            {grrStatus.status === 'acceptable' && <AlertTriangle className="h-3 w-3 text-yellow-600" />}
            {grrStatus.status === 'unacceptable' && <AlertTriangle className="h-3 w-3 text-red-600" />}
            <span className={grrStatus.color}>
              {grrStatus.status === 'excellent' && 'Measurement system is acceptable'}
              {grrStatus.status === 'acceptable' && 'May be acceptable depending on application'}
              {grrStatus.status === 'unacceptable' && 'Measurement system needs improvement'}
            </span>
          </div>
        </div>

        {/* Variation Breakdown Bar Chart */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-medium">
            <span className="text-muted-foreground">Variation Breakdown</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-3 w-3 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs text-xs">
                    Shows the contribution of each source to total variation.
                    Lower EV+AV (GRR) means better measurement system.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          
          {/* Stacked Bar */}
          <div className="h-8 w-full rounded-md overflow-hidden flex">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div 
                    className="bg-blue-500 h-full transition-all" 
                    style={{ width: `${evPercent}%` }}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Equipment Variation (EV): {evPercent.toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Repeatability</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div 
                    className="bg-orange-500 h-full transition-all" 
                    style={{ width: `${avPercent}%` }}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Appraiser Variation (AV): {avPercent.toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Reproducibility</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div 
                    className="bg-green-500 h-full transition-all" 
                    style={{ width: `${pvPercent}%` }}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Part Variation (PV): {pvPercent.toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Actual part-to-part variation</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          
          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-sm bg-blue-500" />
              <span>EV (Repeatability)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-sm bg-orange-500" />
              <span>AV (Reproducibility)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-sm bg-green-500" />
              <span>PV (Part Variation)</span>
            </div>
          </div>
        </div>

        {/* Detailed Metrics Grid */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Repeatability (EV)
            </p>
            <p className="text-lg font-semibold tabular-nums">{result.repeatability_ev.toFixed(4)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Reproducibility (AV)
            </p>
            <p className="text-lg font-semibold tabular-nums">{result.reproducibility_av.toFixed(4)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Part Variation (PV)
            </p>
            <p className="text-lg font-semibold tabular-nums">{result.part_variation_pv.toFixed(4)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Total Variation (TV)
            </p>
            <p className="text-lg font-semibold tabular-nums">{result.total_variation_tv.toFixed(4)}</p>
          </div>
        </div>

        {/* NDC Indicator */}
        <div className="p-4 rounded-lg bg-muted/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Number of Distinct Categories (NDC)
              </p>
              <p className={cn('text-2xl font-bold tabular-nums', ndcStatus.color)}>
                {result.ndc}
              </p>
            </div>
            <div className="text-right">
              {ndcStatus.isAcceptable ? (
                <div className="flex items-center gap-1 text-xs text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  <span>≥ 5 (Acceptable)</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-xs text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span>&lt; 5 (Needs Improvement)</span>
                </div>
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            NDC represents how many distinct part categories the measurement system can reliably distinguish.
            AIAG recommends a minimum of 5 distinct categories.
          </p>
        </div>

        {/* AIAG Guidelines Reference */}
        <div className="text-[10px] text-muted-foreground border-t pt-4">
          <p className="font-bold mb-1">AIAG MSA Guidelines:</p>
          <ul className="space-y-0.5">
            <li className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span>&lt; 10% GRR: Measurement system is acceptable</span>
            </li>
            <li className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-yellow-500" />
              <span>10-30% GRR: May be acceptable based on application importance</span>
            </li>
            <li className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-red-500" />
              <span>&gt; 30% GRR: Measurement system needs improvement</span>
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

// Simple summary badge for use in tables
export function GRRStatusBadge({ grrPercent }: { grrPercent: number }) {
  const status = getGRRStatus(grrPercent);
  
  return (
    <Badge
      variant={status.status === 'excellent' ? 'default' : status.status === 'acceptable' ? 'secondary' : 'destructive'}
      className="text-xs"
    >
      {grrPercent.toFixed(1)}% - {status.label}
    </Badge>
  );
}

// NDC badge for use in tables
export function NDCBadge({ ndc }: { ndc: number }) {
  const status = getNDCStatus(ndc);
  
  return (
    <Badge
      variant={status.isAcceptable ? 'outline' : 'destructive'}
      className={cn('text-xs', status.isAcceptable ? 'border-green-500 text-green-600' : '')}
    >
      NDC: {ndc}
    </Badge>
  );
}
