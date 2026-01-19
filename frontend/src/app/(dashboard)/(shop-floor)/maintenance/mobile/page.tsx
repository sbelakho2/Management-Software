'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Wrench, Scan, AlertTriangle, Clock, ShieldAlert } from 'lucide-react';
import { useMaintenanceStore } from '@/stores';
import { BarcodeScanner, ScanFeedback, type BarcodeScanResult } from '@/components/ui/factory-floor';
import { useI18n } from '@/contexts/i18n-context';

export default function MaintenanceMobilePage() {
  const { t } = useI18n();
  const router = useRouter();
  const { stats, fetchStats } = useMaintenanceStore();
  const [scannerEnabled, setScannerEnabled] = React.useState(false);
  const [lastScan, setLastScan] = React.useState<BarcodeScanResult | null>(null);
  const [scanSuccessVisible, setScanSuccessVisible] = React.useState(false);

  React.useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  React.useEffect(() => {
    if (!scanSuccessVisible) return;
    const timeout = setTimeout(() => setScanSuccessVisible(false), 1500);
    return () => clearTimeout(timeout);
  }, [scanSuccessVisible]);

  return (
    <div className="space-y-6 page-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold tracking-tight">{t('pages.maintenance.mobile.title') || 'Maintenance Mobile'}</h1>
          <p className="text-sm text-muted-foreground">{t('pages.maintenance.mobile.subtitle') || 'Quick actions for floor use'}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => router.push('/maintenance')}>
          {t('common.back') || 'Back'}
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold">{t('pages.maintenance.mobile.openWorkOrders') || 'Open Work Orders'}</CardTitle>
            <Wrench className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-2xl font-bold">{stats?.total_work_orders || 0}</p>
              <Badge variant="secondary">{t('common.assigned') || 'Assigned'}</Badge>
            </div>
            <Button className="mt-3 w-full" size="sm">{t('pages.maintenance.mobile.viewWorkOrders') || 'View Work Orders'}</Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold">{t('pages.maintenance.mobile.pmDue') || 'PM Due'}</CardTitle>
            <Clock className="h-4 w-4 text-rams-orange" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-2xl font-bold">{stats?.overdue_pms || 0}</p>
              <Badge variant="warning">{t('common.overdue') || 'Overdue'}</Badge>
            </div>
            <Button variant="outline" className="mt-3 w-full" size="sm">{t('pages.maintenance.mobile.reviewPMs') || 'Review PMs'}</Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold">{t('pages.maintenance.mobile.activeLOTO') || 'Active LOTO'}</CardTitle>
            <ShieldAlert className="h-4 w-4 text-rams-red" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-2xl font-bold">{stats?.assets_by_status?.down || 0}</p>
              <Badge variant="danger">{t('common.critical') || 'Critical'}</Badge>
            </div>
            <Button variant="outline" className="mt-3 w-full" size="sm">{t('pages.maintenance.mobile.viewLOTO') || 'View LOTO'}</Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold">{t('pages.maintenance.mobile.scanAssetTool') || 'Scan Asset/Tool'}</CardTitle>
            <Scan className="h-4 w-4 text-rams-orange" />
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{t('pages.maintenance.mobile.scanDescription') || 'Use barcode or RFID to open records.'}</p>
            <Button className="mt-3 w-full" size="sm" onClick={() => setScannerEnabled((prev) => !prev)}>
              {scannerEnabled ? (t('pages.maintenance.mobile.stopScanner') || 'Stop Scanner') : (t('pages.maintenance.mobile.launchScanner') || 'Launch Scanner')}
            </Button>
            {scannerEnabled && (
              <div className="mt-4 space-y-3">
                <BarcodeScanner
                  enabled={scannerEnabled}
                  onScan={(result) => {
                    setLastScan(result);
                    setScanSuccessVisible(true);
                  }}
                  scannerType="hardware"
                />
                {lastScan && (
                  <div className="rounded-lg border border-border/60 bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                    Last scan: <span className="font-semibold text-foreground">{lastScan.value}</span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rams-orange" />
            {t('pages.maintenance.mobile.quickIncidentLog') || 'Quick Incident Log'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Button variant="outline" className="w-full" size="sm">{t('pages.maintenance.mobile.logDowntime') || 'Log Downtime'}</Button>
        </CardContent>
      </Card>

      <ScanFeedback visible={scanSuccessVisible} success message="Scan captured" />
    </div>
  );
}
