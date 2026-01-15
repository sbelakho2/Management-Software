'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  FileText,
  Download,
  Search,
  Filter,
  Calendar,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const reports = [
  { id: '1', name: 'Weekly Downtime Analysis', period: 'Jan 1 - Jan 7, 2024', type: 'PDF', size: '1.2 MB' },
  { id: '2', name: 'Monthly Quality Signal Report', period: 'December 2023', type: 'Excel', size: '4.5 MB' },
  { id: '3', name: 'Annual Performance Summary', period: '2023 Full Year', type: 'PDF', size: '12.8 MB' },
];

export default function AndonReportsPage() {
  const router = useRouter();

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">Intelligence Reports</h1>
            <p className="text-muted-foreground font-medium">Generated summaries and organizational performance documents</p>
          </div>
        </div>
        <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
          <FileText className="mr-2 h-4 w-4" />
          Generate Report
        </Button>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
              <Input placeholder="Search reports..." className="pl-11 h-11 bg-background/50 border-border/50 rounded-xl" />
            </div>
            <Button variant="outline" size="icon" className="rounded-xl border-border/50 h-11 w-11">
              <Filter className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {reports.map((report) => (
          <Card key={report.id} className="group hover:-translate-y-1 transition-all duration-300">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="flex items-center gap-5">
                <div className="p-3 bg-primary/10 text-primary rounded-2xl shadow-sm transition-transform duration-500 group-hover:scale-110">
                  <FileText className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-heading font-bold text-base tracking-tight">{report.name}</h3>
                  <div className="flex items-center gap-4 mt-1.5">
                    <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                      <Calendar className="h-3 w-3" />
                      {report.period}
                    </span>
                    <Badge variant="secondary" className="text-[9px] px-1.5">{report.type}</Badge>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{report.size}</span>
                  </div>
                </div>
              </div>
              <Button variant="outline" size="sm" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
                <Download className="mr-2 h-4 w-4" />
                Download
              </Button>
            </CardContent>
          </Card>
        ))}
        {reports.length === 0 && (
          <div className="text-center py-20 bg-muted/5 rounded-[3rem] border-2 border-dashed border-border/20">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-[2rem] bg-muted mb-6">
              <FileText className="h-10 w-10 text-muted-foreground/30" />
            </div>
            <p className="text-sm font-heading font-bold text-muted-foreground/60 tracking-tight">No intelligence reports generated.</p>
          </div>
        )}
      </div>
    </div>
  );
}
