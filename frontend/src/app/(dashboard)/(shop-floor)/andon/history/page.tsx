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

const historyEvents = [
  { id: '1', type: 'Quality', station: 'CNC-04', issue: 'Tension out of spec', resolvedBy: 'Sarah Johnson', duration: '45m', date: '2024-01-12 14:30' },
  { id: '2', type: 'Maintenance', station: 'AS-02', issue: 'Hydraulic leak', resolvedBy: 'Mike Tech', duration: '2h 15m', date: '2024-01-12 09:15' },
  { id: '3', type: 'Material', station: 'ST-01', issue: 'Low stock: Bracket A', resolvedBy: 'Warehouse Team', duration: '15m', date: '2024-01-11 16:45' },
];

export default function AndonHistoryPage() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Andon History</h1>
            <p className="text-muted-foreground">Historical log of all signal events and resolutions</p>
          </div>
        </div>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export History
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search events..." className="pl-9" />
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline">
                <Calendar className="mr-2 h-4 w-4" />
                Date Range
              </Button>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-muted/50 border-b">
                  <th className="p-4 text-left font-medium text-sm">Date & Time</th>
                  <th className="p-4 text-left font-medium text-sm">Type</th>
                  <th className="p-4 text-left font-medium text-sm">Station</th>
                  <th className="p-4 text-left font-medium text-sm">Issue</th>
                  <th className="p-4 text-left font-medium text-sm">Resolved By</th>
                  <th className="p-4 text-center font-medium text-sm">Resolution Time</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {historyEvents.map((event) => (
                  <tr key={event.id} className="hover:bg-muted/30">
                    <td className="p-4 text-sm font-medium">{event.date}</td>
                    <td className="p-4">
                      <Badge variant="secondary">{event.type}</Badge>
                    </td>
                    <td className="p-4 text-sm font-mono">{event.station}</td>
                    <td className="p-4 text-sm">{event.issue}</td>
                    <td className="p-4 text-sm">{event.resolvedBy}</td>
                    <td className="p-4 text-center text-sm font-medium">{event.duration}</td>
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
