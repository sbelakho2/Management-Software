'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useI18n } from '@/contexts/i18n-context';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle, Loader2, Lightbulb, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MicroDrill {
  id: string;
  question: string;
  hint?: string;
}

interface DrillAnswerModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  drill: MicroDrill | null;
  onComplete?: (drillId: string, answer: string) => void;
}

export function DrillAnswerModal({
  open,
  onOpenChange,
  drill,
  onComplete,
}: DrillAnswerModalProps) {
  const { t } = useI18n();
  const { toast } = useToast();
  const [answer, setAnswer] = React.useState('');
  const [showHint, setShowHint] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isCompleted, setIsCompleted] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setAnswer('');
      setShowHint(false);
      setIsSubmitting(false);
      setIsCompleted(false);
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!drill || !answer.trim()) return;

    setIsSubmitting(true);

    // Simulate API call to submit the answer
    await new Promise((resolve) => setTimeout(resolve, 1000));

    setIsSubmitting(false);
    setIsCompleted(true);

    toast({
      title: t('pages.today.drill.completed'),
      description: t('pages.today.drill.keepMomentum'),
    });

    if (onComplete) {
      onComplete(drill.id, answer);
    }

    // Auto-close after showing success state
    setTimeout(() => {
      onOpenChange(false);
    }, 1500);
  };

  if (!drill) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] rounded-none border-rams-line bg-rams-chassis">
        <DialogHeader className="border-b border-rams-line pb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-rams-orange rounded-none">
              <Zap className="h-4 w-4 text-black" />
            </div>
            <span className="text-[8px] font-black uppercase tracking-widest px-2 py-1 border border-rams-line bg-rams-panel">
              {t('pages.today.drill.dailyProtocol')}
            </span>
          </div>
          <DialogTitle className="font-sans font-black text-lg uppercase tracking-tight">
            {t('pages.today.drill.title')}
          </DialogTitle>
          <DialogDescription className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">
            {t('pages.today.drill.engageQuestion')}
          </DialogDescription>
        </DialogHeader>

        {isCompleted ? (
          <div className="py-12 flex flex-col items-center gap-4 animate-in fade-in duration-300">
            <div className="p-4 rounded-none bg-green-500/10 border border-green-500/20">
              <CheckCircle className="h-12 w-12 text-green-500" />
            </div>
            <p className="font-sans font-black uppercase tracking-tight text-green-500">
              {t('pages.today.drill.drillComplete')}
            </p>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60">
              {t('pages.today.drill.responseRecorded')}
            </p>
          </div>
        ) : (
          <>
            <div className="py-6 space-y-6">
              <div className="p-4 bg-rams-panel border border-rams-line">
                <p className="font-sans font-bold text-sm leading-relaxed text-foreground/90">
                  {drill.question}
                </p>
              </div>

              {drill.hint && (
                <div>
                  <button
                    onClick={() => setShowHint(!showHint)}
                    className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-rams-orange hover:text-rams-orange/80 transition-colors"
                  >
                    <Lightbulb className="h-3 w-3" />
                    {showHint ? t('pages.today.drill.hideHint') : t('pages.today.drill.showHint')}
                  </button>
                  {showHint && (
                    <div className="mt-2 p-3 bg-rams-orange/10 border border-rams-orange/20 animate-in slide-in-from-top-2 duration-200">
                      <p className="text-xs text-rams-orange/90 font-medium">
                        {drill.hint}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                  {t('pages.today.drill.yourResponse')}
                </label>
                <Textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder={t('pages.today.drill.responsePlaceholder')}
                  className={cn(
                    'min-h-[120px] resize-none rounded-none border-rams-line bg-rams-module',
                    'placeholder:text-muted-foreground/30 placeholder:font-mono placeholder:text-xs',
                    'focus:border-rams-orange focus:ring-1 focus:ring-rams-orange'
                  )}
                />
              </div>
            </div>

            <DialogFooter className="border-t border-rams-line pt-6 gap-2">
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                className="rounded-none border-rams-line text-[10px] font-black uppercase tracking-widest"
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!answer.trim() || isSubmitting}
                className="rounded-none bg-rams-orange text-black hover:bg-rams-orange/90 text-[10px] font-black uppercase tracking-widest"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                    {t('pages.today.drill.submitting')}
                  </>
                ) : (
                  t('pages.today.drill.submitResponse')
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
