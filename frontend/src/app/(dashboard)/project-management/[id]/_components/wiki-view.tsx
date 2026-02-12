'use client';

import * as React from 'react';
import { useProjectManagementStore, type WikiPage } from '@/stores/project-management-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, Search, FileText, ChevronRight, Edit3, Save, X, Trash2 } from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useI18n } from '@/contexts/i18n-context';

interface WikiViewProps {
  projectId: string;
}

export function WikiView({ projectId }: WikiViewProps) {
  const { 
    wikiPages, fetchWikiPages, createWikiPage, updateWikiPage
  } = useProjectManagementStore();
  const { t } = useI18n();
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedPage, setSelectedPage] = React.useState<WikiPage | null>(null);
  const [isEditing, setIsEditing] = React.useState(false);
  const [editForm, setEditForm] = React.useState({ title: '', content: '' });
  const [isCreating, setIsCreating] = React.useState(false);

  React.useEffect(() => {
    if (projectId) {
      fetchWikiPages(projectId);
    }
  }, [projectId, fetchWikiPages]);

  const filteredPages = wikiPages.filter(p => 
    p.project_id === projectId && 
    p.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handlePageSelect = (page: WikiPage) => {
    setSelectedPage(page);
    setIsEditing(false);
    setIsCreating(false);
  };

  const handleStartEdit = () => {
    if (!selectedPage) return;
    setEditForm({ title: selectedPage.title, content: selectedPage.content });
    setIsEditing(true);
  };

  const handleStartCreate = () => {
    setEditForm({ title: '', content: '' });
    setIsCreating(true);
    setIsEditing(false);
    setSelectedPage(null);
  };

  const handleSave = async () => {
    if (!editForm.title.trim()) return;

    try {
      if (isCreating) {
        const created = await createWikiPage({
          project_id: projectId,
          title: editForm.title,
          content: editForm.content,
        });
        setSelectedPage(created);
        setIsCreating(false);
      } else if (selectedPage) {
        const updated = await updateWikiPage(selectedPage.id, {
          title: editForm.title,
          content: editForm.content,
        });
        setSelectedPage(updated);
        setIsEditing(false);
      }
    } catch (error) {
      console.error('Failed to save wiki page:', error);
    }
  };

  return (
    <div className="flex h-[calc(100vh-200px)] border rounded-lg overflow-hidden bg-background">
      {/* Sidebar */}
      <div className="w-64 border-r flex flex-col bg-secondary/10">
        <div className="p-4 border-b space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">{t('pages.projectManagement.wiki.pages')}</h3>
            <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleStartCreate}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-3 w-3 text-muted-foreground" />
            <Input 
              placeholder={t('pages.projectManagement.wiki.searchPlaceholder')} 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-7 h-8 text-xs" 
            />
          </div>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {filteredPages.map(page => (
              <button
                key={page.id}
                onClick={() => handlePageSelect(page)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors text-left",
                  selectedPage?.id === page.id ? "bg-primary text-primary-foreground" : "hover:bg-accent"
                )}
              >
                <FileText className="h-4 w-4 shrink-0" />
                <span className="truncate">{page.title}</span>
              </button>
            ))}
            {filteredPages.length === 0 && (
              <p className="text-xs text-center text-muted-foreground py-4">{t('pages.projectManagement.wiki.noPagesFound')}</p>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {(selectedPage || isCreating) ? (
          <>
            <div className="p-4 border-b flex items-center justify-between bg-background">
              <div className="flex-1 min-w-0">
                {isEditing || isCreating ? (
                  <Input 
                    value={editForm.title}
                    onChange={(e) => setEditForm(prev => ({ ...editForm, title: e.target.value }))}
                    placeholder={t('pages.projectManagement.wiki.titlePlaceholder')}
                    className="text-xl font-bold h-10"
                  />
                ) : (
                  <h2 className="text-xl font-bold truncate">{selectedPage?.title}</h2>
                )}
              </div>
              <div className="flex items-center gap-2 ml-4">
                {isEditing || isCreating ? (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => { setIsEditing(false); setIsCreating(false); }}>
                      <X className="h-4 w-4 mr-2" /> {t('common.cancel')}
                    </Button>
                    <Button size="sm" onClick={handleSave}>
                      <Save className="h-4 w-4 mr-2" /> {t('common.save')}
                    </Button>
                  </>
                ) : (
                  <Button variant="outline" size="sm" onClick={handleStartEdit}>
                    <Edit3 className="h-4 w-4 mr-2" /> {t('common.edit')}
                  </Button>
                )}
              </div>
            </div>
            <ScrollArea className="flex-1 p-6">
              <div className="max-w-3xl mx-auto">
                {isEditing || isCreating ? (
                  <Textarea 
                    value={editForm.content}
                    onChange={(e) => setEditForm(prev => ({ ...editForm, content: e.target.value }))}
                    placeholder={t('pages.projectManagement.wiki.contentPlaceholder')}
                    className="min-h-[400px] font-mono"
                  />
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <p className="whitespace-pre-wrap">{selectedPage?.content}</p>
                    <div className="mt-10 pt-6 border-t text-xs text-muted-foreground">
                      {t('pages.projectManagement.wiki.lastUpdated')} {selectedPage && formatRelativeTime(selectedPage.updated_at)} • {t('pages.projectManagement.wiki.version')} {selectedPage?.version}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-4">
            <FileText className="h-12 w-12 opacity-20" />
            <div className="text-center">
              <h3 className="font-medium">{t('pages.projectManagement.wiki.noPageSelected')}</h3>
              <p className="text-sm">{t('pages.projectManagement.wiki.selectAPage')}</p>
            </div>
            <Button variant="outline" onClick={handleStartCreate}>
              <Plus className="h-4 w-4 mr-2" /> {t('pages.projectManagement.wiki.createFirstPage')}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
