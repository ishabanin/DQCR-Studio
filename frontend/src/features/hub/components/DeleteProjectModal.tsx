import { useState } from "react";

import { AlertDialog, AlertDialogBody, AlertDialogContent, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "../../../shared/components/ui/AlertDialog";
import Button from "../../../shared/components/ui/Button";
import Input from "../../../shared/components/ui/Input";
import type { ProjectListItem } from "../types";

const DELETE_WARNING = {
  internal: "This will permanently delete all project files from the workspace.",
  imported: "This will remove the imported copy from the workspace. The original source directory will not be affected.",
  linked: "This will remove the link from the workspace registry. The original directory at the linked path will not be affected.",
} as const;

interface DeleteProjectModalProps {
  project: ProjectListItem;
  onClose: () => void;
  onSubmit: () => Promise<void>;
  isSubmitting: boolean;
}

export function DeleteProjectModal({ project, onClose, onSubmit, isSubmitting }: DeleteProjectModalProps) {
  const [confirmValue, setConfirmValue] = useState("");
  const canDelete = confirmValue === project.project_id;

  return (
    <AlertDialog open onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <AlertDialogContent className="hub-alert-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Delete project</AlertDialogTitle>
        </AlertDialogHeader>

        <AlertDialogBody className="hub-dialog-body">
          <div className="hub-delete-warning">
            <strong>You are about to delete {project.name}.</strong> {DELETE_WARNING[project.project_type]} <strong>This action cannot be undone.</strong>
          </div>

          <div className="hub-form-row">
            <label className="hub-form-label">Type project name to confirm:</label>
            <Input
              placeholder={project.project_id}
              value={confirmValue}
              onChange={(event) => setConfirmValue(event.target.value)}
              className={confirmValue === "" ? "" : canDelete ? "hub-input-ok" : "hub-input-error"}
            />
          </div>
        </AlertDialogBody>

        <AlertDialogFooter className="hub-dialog-footer">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" disabled={!canDelete || isSubmitting} onClick={onSubmit}>
            {isSubmitting ? "Deleting..." : "Delete project"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
