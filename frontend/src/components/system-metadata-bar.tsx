'use client';

import { useI18n } from '@/contexts/i18n-context';

const SYSTEM_METADATA = {
  station: 'SENSEI-ALPHA-01',
  osVer: '3.0.0-RAMS',
  integrity: 'OPTIMAL',
  latency: '14MS',
};

export function SystemMetadataBar() {
  const { t } = useI18n();

  return (
    <div className="fixed bottom-0 left-0 right-0 h-8 bg-rams-chassis z-[100] border-t border-rams-line px-6 hidden md:flex items-center justify-between text-[10px] font-mono opacity-60 uppercase tracking-widest pointer-events-none">
      <div className="flex gap-6">
        <span>{t('layout.systemMetadata.station', { station: SYSTEM_METADATA.station })}</span>
        <span>{t('layout.systemMetadata.osVer', { version: SYSTEM_METADATA.osVer })}</span>
      </div>
      <div className="flex gap-6">
        <span>{t('layout.systemMetadata.integrity', { state: SYSTEM_METADATA.integrity })}</span>
        <span>{t('layout.systemMetadata.latency', { latency: SYSTEM_METADATA.latency })}</span>
      </div>
    </div>
  );
}
