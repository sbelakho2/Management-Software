//! Project management store — projects, epics, sprints, user stories,
//! subtasks, issues, wiki pages, milestones, and activities.
//!
//! Port of [`frontend/src/stores/project-management-store.ts`](frontend/src/stores/project-management-store.ts).

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use std::collections::HashSet;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub description: String,
    pub status: String,
    pub priority: String,
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub owner_id: String,
    pub owner_name: Option<String>,
    pub team_members: Vec<String>,
    pub tags: Vec<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Epic {
    pub id: String,
    pub project_id: String,
    pub subject: String,
    pub description: String,
    pub status: String,
    pub priority: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Sprint {
    pub id: String,
    pub project_id: String,
    pub name: String,
    pub goal: Option<String>,
    pub start_date: String,
    pub end_date: String,
    pub status: String,
    pub velocity: Option<f64>,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct UserStory {
    pub id: String,
    pub project_id: String,
    pub epic_id: Option<String>,
    pub sprint_id: Option<String>,
    pub subject: String,
    pub description: String,
    pub status: String,
    pub priority: String,
    pub story_points: Option<f64>,
    pub assignee_id: Option<String>,
    pub assignee_name: Option<String>,
    pub due_date: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Subtask {
    pub id: String,
    pub story_id: String,
    pub subject: String,
    pub description: String,
    pub status: String,
    pub assignee_id: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct StoryComment {
    pub id: String,
    pub story_id: String,
    pub author_id: String,
    pub author_name: String,
    pub content: String,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Issue {
    pub id: String,
    pub project_id: String,
    pub title: String,
    pub description: String,
    pub status: String,
    pub priority: String,
    pub issue_type: String,
    pub assignee_id: Option<String>,
    pub assignee_name: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct IssueComment {
    pub id: String,
    pub issue_id: String,
    pub author_id: String,
    pub author_name: String,
    pub content: String,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct WikiPage {
    pub id: String,
    pub project_id: String,
    pub title: String,
    pub content: String,
    pub slug: String,
    pub parent_id: Option<String>,
    pub author_id: String,
    pub author_name: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProjectMilestone {
    pub id: String,
    pub project_id: String,
    pub name: String,
    pub description: String,
    pub due_date: String,
    pub status: String,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProjectActivity {
    pub id: String,
    pub project_id: String,
    pub user_id: String,
    pub user_name: String,
    pub action: String,
    pub entity_type: String,
    pub entity_id: String,
    pub details: Option<serde_json::Value>,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ApiEnvelope<T> {
    pub data: T,
    pub message: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ApiPaginated<T> {
    pub items: Vec<T>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
}

// ---------------------------------------------------------------------------
// ProjectManagementStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ProjectManagementStore {
    // Data
    pub projects: RwSignal<Vec<Project>>,
    pub current_project: RwSignal<Option<Project>>,
    pub epics: RwSignal<Vec<Epic>>,
    pub sprints: RwSignal<Vec<Sprint>>,
    pub stories: RwSignal<Vec<UserStory>>,
    pub subtasks: RwSignal<Vec<Subtask>>,
    pub story_comments: RwSignal<Vec<StoryComment>>,
    pub issues: RwSignal<Vec<Issue>>,
    pub issue_comments: RwSignal<Vec<IssueComment>>,
    pub wiki_pages: RwSignal<Vec<WikiPage>>,
    pub milestones: RwSignal<Vec<ProjectMilestone>>,
    pub activities: RwSignal<Vec<ProjectActivity>>,
    pub my_work: RwSignal<Vec<UserStory>>,

    // Loading & error
    pub loading_ops: RwSignal<HashSet<String>>,
    pub error: RwSignal<Option<String>>,
}

impl ProjectManagementStore {
    pub fn new() -> Self {
        Self {
            projects: RwSignal::new(Vec::new()),
            current_project: RwSignal::new(None),
            epics: RwSignal::new(Vec::new()),
            sprints: RwSignal::new(Vec::new()),
            stories: RwSignal::new(Vec::new()),
            subtasks: RwSignal::new(Vec::new()),
            story_comments: RwSignal::new(Vec::new()),
            issues: RwSignal::new(Vec::new()),
            issue_comments: RwSignal::new(Vec::new()),
            wiki_pages: RwSignal::new(Vec::new()),
            milestones: RwSignal::new(Vec::new()),
            activities: RwSignal::new(Vec::new()),
            my_work: RwSignal::new(Vec::new()),
            loading_ops: RwSignal::new(HashSet::new()),
            error: RwSignal::new(None),
        }
    }

    fn start_op(&self, op: &str) {
        self.loading_ops.update(|ops| {
            ops.insert(op.to_string());
        });
        self.error.set(None);
    }

    fn end_op(&self, op: &str) {
        self.loading_ops.update(|ops| {
            ops.remove(op);
        });
    }

    pub fn is_op_loading(&self, op: &str) -> bool {
        self.loading_ops.get().contains(op)
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }

    // -----------------------------------------------------------------------
    // Projects
    // -----------------------------------------------------------------------

    pub async fn fetch_projects(&self, client: &ApiClient) {
        self.start_op("fetchProjects");
        match client.get::<Vec<Project>>("/projects").await {
            Ok(items) => self.projects.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchProjects");
    }

    pub async fn fetch_project_by_id(&self, client: &ApiClient, id: &str) {
        self.start_op("fetchProjectById");
        match client.get::<Project>(&format!("/projects/{id}")).await {
            Ok(project) => {
                self.current_project.set(Some(project));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchProjectById");
    }

    pub async fn create_project(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<Project, ApiError> {
        self.start_op("createProject");
        match client
            .post::<Project, serde_json::Value>("/projects", &payload)
            .await
        {
            Ok(project) => {
                self.projects.update(|p| p.push(project.clone()));
                self.end_op("createProject");
                Ok(project)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createProject");
                Err(e)
            }
        }
    }

    pub async fn update_project(
        &self,
        client: &ApiClient,
        id: &str,
        updates: serde_json::Value,
    ) -> Result<Project, ApiError> {
        self.start_op("updateProject");
        match client
            .put::<Project, serde_json::Value>(&format!("/projects/{id}"), &updates)
            .await
        {
            Ok(updated) => {
                self.projects.update(|p| {
                    if let Some(pos) = p.iter().position(|x| x.id == id) {
                        p[pos] = updated.clone();
                    }
                });
                self.end_op("updateProject");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateProject");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Epics
    // -----------------------------------------------------------------------

    pub async fn fetch_epics(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchEpics");
        match client
            .get::<Vec<Epic>>(&format!("/projects/{project_id}/epics"))
            .await
        {
            Ok(items) => self.epics.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchEpics");
    }

    pub async fn create_epic(
        &self,
        client: &ApiClient,
        project_id: &str,
        subject: &str,
        description: &str,
    ) -> Result<Epic, ApiError> {
        self.start_op("createEpic");
        let payload = serde_json::json!({ "subject": subject, "description": description });
        match client
            .post::<Epic, serde_json::Value>(&format!("/projects/{project_id}/epics"), &payload)
            .await
        {
            Ok(epic) => {
                self.epics.update(|e| e.push(epic.clone()));
                self.end_op("createEpic");
                Ok(epic)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createEpic");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Sprints
    // -----------------------------------------------------------------------

    pub async fn fetch_sprints(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchSprints");
        match client
            .get::<Vec<Sprint>>(&format!("/projects/{project_id}/sprints"))
            .await
        {
            Ok(items) => self.sprints.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchSprints");
    }

    pub async fn create_sprint(
        &self,
        client: &ApiClient,
        project_id: &str,
        name: &str,
        start_date: &str,
        end_date: &str,
    ) -> Result<Sprint, ApiError> {
        self.start_op("createSprint");
        let payload = serde_json::json!({
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
        });
        match client
            .post::<Sprint, serde_json::Value>(&format!("/projects/{project_id}/sprints"), &payload)
            .await
        {
            Ok(sprint) => {
                self.sprints.update(|s| s.push(sprint.clone()));
                self.end_op("createSprint");
                Ok(sprint)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createSprint");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Stories
    // -----------------------------------------------------------------------

    pub async fn fetch_stories(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchStories");
        match client
            .get::<Vec<UserStory>>(&format!("/projects/{project_id}/stories"))
            .await
        {
            Ok(items) => self.stories.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchStories");
    }

    pub async fn create_story(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<UserStory, ApiError> {
        self.start_op("createStory");
        match client
            .post::<UserStory, serde_json::Value>("/stories", &payload)
            .await
        {
            Ok(story) => {
                self.stories.update(|s| s.push(story.clone()));
                self.end_op("createStory");
                Ok(story)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createStory");
                Err(e)
            }
        }
    }

    pub async fn update_story(
        &self,
        client: &ApiClient,
        story_id: &str,
        updates: serde_json::Value,
    ) -> Result<UserStory, ApiError> {
        self.start_op("updateStory");
        match client
            .put::<UserStory, serde_json::Value>(&format!("/stories/{story_id}"), &updates)
            .await
        {
            Ok(updated) => {
                self.stories.update(|s| {
                    if let Some(pos) = s.iter().position(|x| x.id == story_id) {
                        s[pos] = updated.clone();
                    }
                });
                self.end_op("updateStory");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateStory");
                Err(e)
            }
        }
    }

    pub async fn update_story_status(
        &self,
        client: &ApiClient,
        story_id: &str,
        status: &str,
    ) -> Result<UserStory, ApiError> {
        self.update_story(client, story_id, serde_json::json!({ "status": status }))
            .await
    }

    // -----------------------------------------------------------------------
    // Issues
    // -----------------------------------------------------------------------

    pub async fn fetch_issues(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchIssues");
        match client
            .get::<Vec<Issue>>(&format!("/projects/{project_id}/issues"))
            .await
        {
            Ok(items) => self.issues.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchIssues");
    }

    pub async fn create_issue(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<Issue, ApiError> {
        self.start_op("createIssue");
        match client
            .post::<Issue, serde_json::Value>("/issues", &payload)
            .await
        {
            Ok(issue) => {
                self.issues.update(|i| i.push(issue.clone()));
                self.end_op("createIssue");
                Ok(issue)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createIssue");
                Err(e)
            }
        }
    }

    pub async fn update_issue(
        &self,
        client: &ApiClient,
        issue_id: &str,
        updates: serde_json::Value,
    ) -> Result<Issue, ApiError> {
        self.start_op("updateIssue");
        match client
            .put::<Issue, serde_json::Value>(&format!("/issues/{issue_id}"), &updates)
            .await
        {
            Ok(updated) => {
                self.issues.update(|i| {
                    if let Some(pos) = i.iter().position(|x| x.id == issue_id) {
                        i[pos] = updated.clone();
                    }
                });
                self.end_op("updateIssue");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateIssue");
                Err(e)
            }
        }
    }

    pub async fn fetch_issue_comments(&self, client: &ApiClient, issue_id: &str) {
        self.start_op("fetchIssueComments");
        match client
            .get::<Vec<IssueComment>>(&format!("/issues/{issue_id}/comments"))
            .await
        {
            Ok(items) => self.issue_comments.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchIssueComments");
    }

    pub async fn create_issue_comment(
        &self,
        client: &ApiClient,
        issue_id: &str,
        content: &str,
    ) -> Result<IssueComment, ApiError> {
        self.start_op("createIssueComment");
        let payload = serde_json::json!({ "content": content });
        match client
            .post::<IssueComment, serde_json::Value>(
                &format!("/issues/{issue_id}/comments"),
                &payload,
            )
            .await
        {
            Ok(comment) => {
                self.issue_comments.update(|c| c.push(comment.clone()));
                self.end_op("createIssueComment");
                Ok(comment)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createIssueComment");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Wiki Pages
    // -----------------------------------------------------------------------

    pub async fn fetch_wiki_pages(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchWikiPages");
        match client
            .get::<Vec<WikiPage>>(&format!("/projects/{project_id}/wiki"))
            .await
        {
            Ok(items) => self.wiki_pages.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchWikiPages");
    }

    pub async fn create_wiki_page(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<WikiPage, ApiError> {
        self.start_op("createWikiPage");
        match client
            .post::<WikiPage, serde_json::Value>("/wiki", &payload)
            .await
        {
            Ok(page) => {
                self.wiki_pages.update(|w| w.push(page.clone()));
                self.end_op("createWikiPage");
                Ok(page)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createWikiPage");
                Err(e)
            }
        }
    }

    pub async fn update_wiki_page(
        &self,
        client: &ApiClient,
        page_id: &str,
        updates: serde_json::Value,
    ) -> Result<WikiPage, ApiError> {
        self.start_op("updateWikiPage");
        match client
            .put::<WikiPage, serde_json::Value>(&format!("/wiki/{page_id}"), &updates)
            .await
        {
            Ok(updated) => {
                self.wiki_pages.update(|w| {
                    if let Some(pos) = w.iter().position(|x| x.id == page_id) {
                        w[pos] = updated.clone();
                    }
                });
                self.end_op("updateWikiPage");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateWikiPage");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Milestones
    // -----------------------------------------------------------------------

    pub async fn fetch_milestones(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchMilestones");
        match client
            .get::<Vec<ProjectMilestone>>(&format!("/projects/{project_id}/milestones"))
            .await
        {
            Ok(items) => self.milestones.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchMilestones");
    }

    pub async fn create_milestone(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<ProjectMilestone, ApiError> {
        self.start_op("createMilestone");
        match client
            .post::<ProjectMilestone, serde_json::Value>("/milestones", &payload)
            .await
        {
            Ok(milestone) => {
                self.milestones.update(|m| m.push(milestone.clone()));
                self.end_op("createMilestone");
                Ok(milestone)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createMilestone");
                Err(e)
            }
        }
    }

    pub async fn update_milestone(
        &self,
        client: &ApiClient,
        milestone_id: &str,
        updates: serde_json::Value,
    ) -> Result<ProjectMilestone, ApiError> {
        self.start_op("updateMilestone");
        match client
            .put::<ProjectMilestone, serde_json::Value>(
                &format!("/milestones/{milestone_id}"),
                &updates,
            )
            .await
        {
            Ok(updated) => {
                self.milestones.update(|m| {
                    if let Some(pos) = m.iter().position(|x| x.id == milestone_id) {
                        m[pos] = updated.clone();
                    }
                });
                self.end_op("updateMilestone");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateMilestone");
                Err(e)
            }
        }
    }

    pub async fn delete_milestone(
        &self,
        client: &ApiClient,
        milestone_id: &str,
    ) -> Result<(), ApiError> {
        self.start_op("deleteMilestone");
        match client
            .delete::<serde_json::Value>(&format!("/milestones/{milestone_id}"))
            .await
        {
            Ok(_) => {
                self.milestones
                    .update(|m| m.retain(|x| x.id != milestone_id));
                self.end_op("deleteMilestone");
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("deleteMilestone");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Activities
    // -----------------------------------------------------------------------

    pub async fn fetch_activities(&self, client: &ApiClient, project_id: &str) {
        self.start_op("fetchActivities");
        match client
            .get::<Vec<ProjectActivity>>(&format!("/projects/{project_id}/activities"))
            .await
        {
            Ok(items) => self.activities.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchActivities");
    }

    // -----------------------------------------------------------------------
    // My Work
    // -----------------------------------------------------------------------

    pub async fn fetch_my_work(&self, client: &ApiClient) {
        self.start_op("fetchMyWork");
        match client.get::<Vec<UserStory>>("/my-work").await {
            Ok(items) => self.my_work.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchMyWork");
    }

    // -----------------------------------------------------------------------
    // Subtasks
    // -----------------------------------------------------------------------

    pub async fn fetch_subtasks(&self, client: &ApiClient, story_id: &str) {
        self.start_op("fetchSubtasks");
        match client
            .get::<Vec<Subtask>>(&format!("/stories/{story_id}/subtasks"))
            .await
        {
            Ok(items) => self.subtasks.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchSubtasks");
    }

    pub async fn create_subtask(
        &self,
        client: &ApiClient,
        story_id: &str,
        subject: &str,
        description: &str,
        status: &str,
    ) -> Result<Subtask, ApiError> {
        self.start_op("createSubtask");
        let payload = serde_json::json!({
            "story_id": story_id,
            "subject": subject,
            "description": description,
            "status": status,
        });
        match client
            .post::<Subtask, serde_json::Value>(&format!("/stories/{story_id}/subtasks"), &payload)
            .await
        {
            Ok(subtask) => {
                self.subtasks.update(|s| s.push(subtask.clone()));
                self.end_op("createSubtask");
                Ok(subtask)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createSubtask");
                Err(e)
            }
        }
    }

    pub async fn update_subtask(
        &self,
        client: &ApiClient,
        subtask_id: &str,
        updates: serde_json::Value,
    ) -> Result<Subtask, ApiError> {
        self.start_op("updateSubtask");
        match client
            .put::<Subtask, serde_json::Value>(&format!("/subtasks/{subtask_id}"), &updates)
            .await
        {
            Ok(updated) => {
                self.subtasks.update(|s| {
                    if let Some(pos) = s.iter().position(|x| x.id == subtask_id) {
                        s[pos] = updated.clone();
                    }
                });
                self.end_op("updateSubtask");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateSubtask");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Story Comments
    // -----------------------------------------------------------------------

    pub async fn fetch_story_comments(&self, client: &ApiClient, story_id: &str) {
        self.start_op("fetchStoryComments");
        match client
            .get::<Vec<StoryComment>>(&format!("/stories/{story_id}/comments"))
            .await
        {
            Ok(items) => self.story_comments.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchStoryComments");
    }

    pub async fn create_story_comment(
        &self,
        client: &ApiClient,
        story_id: &str,
        content: &str,
    ) -> Result<StoryComment, ApiError> {
        self.start_op("createStoryComment");
        let payload = serde_json::json!({ "content": content });
        match client
            .post::<StoryComment, serde_json::Value>(
                &format!("/stories/{story_id}/comments"),
                &payload,
            )
            .await
        {
            Ok(comment) => {
                self.story_comments.update(|c| c.push(comment.clone()));
                self.end_op("createStoryComment");
                Ok(comment)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createStoryComment");
                Err(e)
            }
        }
    }
}

impl Default for ProjectManagementStore {
    fn default() -> Self {
        Self::new()
    }
}
