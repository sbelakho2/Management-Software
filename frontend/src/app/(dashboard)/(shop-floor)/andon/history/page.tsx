'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Calendar,
  Filter,
  Search,
  Download,
  Clock,
  CheckCircle2,
  AlertTriangle,
  History,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn, formatDate } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

const historyEvents = [
  { id: '1', type: 'Quality', station: 'CNC-04', issue: 'Tension out of spec', resolvedBy: 'Sarah Johnson', duration: '45m', date: '2024-01-12 14:30' },
  { id: '2', type: 'Maintenance', station: 'AS-02', issue: 'Hydraulic leak', resolvedBy: 'Mike Tech', duration: '2h 15m', date: '2024-01-12 09:15' },
  { id: '3', type: 'Material', station: 'ST-01', issue: 'Low stock: Bracket A', resolvedBy: 'Warehouse Team', duration: '15m', date: '2024-01-11 16:45' },
];

export default function AndonHistoryPage() {
  const { t } = useI18n();
  const router = useRouter();

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">Anomalous History</h1>
            <p className="text-muted-foreground font-medium text-sm">Historical log of organizational signal events and resolution protocols</p>
          </div>
        </div>
        <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
          <Download className="mr-2 h-4 w-4" />
          Export Telemetry
        </Button>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
              <Input placeholder="Search event nodes..." className="pl-11 h-12 bg-background/50 border-border/50 rounded-xl" />
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="lg" className="rounded-xl border-border/50 h-12">
                <Calendar className="mr-2 h-4 w-4" />
                Strategic Window
              </Button>
              <Button variant="outline" size="icon" className="h-12 w-12 rounded-xl border-border/50">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="p-5 text-left">Temporal Node</th>
                  <th className="p-5 text-left">Signal Type</th>
                  <th className="p-5 text-left">Station Node</th>
                  <th className="p-5 text-left">Anomalous Context</th>
                  <th className="p-5 text-left">Resolution Agent</th>
                  <th className="p-5 text-center">Protocol Duration</th>
                </tr>
              </thead>
              <tbody>
                {historyEvents.map((event) => (
                  <tr key={event.id} className="group hover:bg-primary/5 transition-all duration-300">
                    <td className="p-5 text-sm font-medium text-foreground/80">{event.date}</td>
                    <td className="p-5">
                      <Badge variant="secondary" className="text-[9px] font-black uppercase tracking-widest bg-background/50">{event.type}</Badge>
                    </td>
                    <td className="p-5 text-sm font-mono font-bold text-primary/60">{event.station}</td>
                    <td className="p-5 text-sm font-medium text-foreground/70">{event.issue}</td>
                    <td className="p-5 text-sm font-medium text-foreground/70">{event.resolvedBy}</td>
                    <td className="p-5 text-center">
                      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/5 text-primary text-[10px] font-bold">
                        <Clock className="h-3 w-3" />
                        {event.duration}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
