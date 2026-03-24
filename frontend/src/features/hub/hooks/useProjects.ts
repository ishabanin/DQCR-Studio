import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createProject,
  deleteProject,
  fetchProjects,
  patchProjectMetadata,
  uploadProjectFolder,
  type ProjectItem,
} from "../../../api/projects";
import { useProjectStore } from "../../../app/store/projectStore";
import { useUiStore } from "../../../app/store/uiStore";
import type { CreateProjectPayload, MetadataUpdatePayload, ProjectListItem } from "../types";

function mapProject(item: ProjectItem): ProjectListItem {
  return {
    project_id: item.id,
    name: item.name,
    description: item.description ?? null,
    project_type: (item.project_type ?? item.source_type ?? "internal") as ProjectListItem["project_type"],
    visibility: (item.visibility ?? "private") as ProjectListItem["visibility"],
    tags: Array.isArray(item.tags) ? item.tags : [],
    cache_status: (item.cache_status ?? "missing") as ProjectListItem["cache_status"],
    model_count: item.model_count ?? 0,
    folder_count: item.folder_count ?? 0,
    sql_count: item.sql_count ?? 0,
    modified_at: item.modified_at ?? new Date(0).toISOString(),
    source_path: item.source_path ?? null,
    availability_status: item.availability_status,
  };
}

export function useProjects() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((state) => state.addToast);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: async (): Promise<ProjectListItem[]> => (await fetchProjects()).map(mapProject),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateProjectPayload) => createProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      addToast("Project created", "success");
    },
    onError: () => addToast("Failed to create project", "error"),
  });

  const importMutation = useMutation({
    mutationFn: (payload: {
      files: File[];
      relativePaths: string[];
      project_id?: string;
      name?: string;
      description?: string;
    }) =>
      uploadProjectFolder({
        files: payload.files,
        relativePaths: payload.relativePaths,
        project_id: payload.project_id,
        name: payload.name,
        description: payload.description,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      addToast("Project imported", "success");
    },
    onError: () => addToast("Failed to import project", "error"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ projectId, data }: { projectId: string; data: MetadataUpdatePayload }) => patchProjectMetadata(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      addToast("Project updated", "success");
    },
    onError: () => addToast("Failed to update project", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: (projectId: string) => deleteProject(projectId),
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      addToast("Project removed from workspace", "success");
      if (useProjectStore.getState().currentProjectId === projectId) {
        useProjectStore.getState().setProject(null);
      }
    },
    onError: () => addToast("Failed to delete project", "error"),
  });

  return {
    projects: projectsQuery.data ?? [],
    isLoading: projectsQuery.isLoading,
    isError: projectsQuery.isError,
    error: (projectsQuery.error as Error | null) ?? null,
    refetch: projectsQuery.refetch,
    createProject: createMutation.mutateAsync,
    importProject: importMutation.mutateAsync,
    updateProject: updateMutation.mutateAsync,
    deleteProject: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isImporting: importMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
