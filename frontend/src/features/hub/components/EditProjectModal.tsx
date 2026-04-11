import { useEffect, useState } from "react";

import Badge from "../../../shared/components/ui/Badge";
import Button from "../../../shared/components/ui/Button";
import Input from "../../../shared/components/ui/Input";
import { DialogBody, DialogFooter } from "../../../shared/components/ui/Dialog";
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "../../../shared/components/ui/Sheet";
import type { MetadataUpdatePayload, ProjectListItem } from "../types";
import { TagsInput } from "./TagsInput";
import { VisibilitySelector } from "./VisibilitySelector";

interface EditProjectModalProps {
  project: ProjectListItem;
  tagSuggestions: string[];
  onClose: () => void;
  onSubmit: (payload: MetadataUpdatePayload) => Promise<void>;
  isSubmitting: boolean;
}

function useIsMobileSheet() {
  const [isMobile, setIsMobile] = useState<boolean>(() => window.matchMedia("(max-width: 767px)").matches);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const handler = () => setIsMobile(query.matches);
    handler();
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }, []);

  return isMobile;
}

export function EditProjectModal({ project, tagSuggestions, onClose, onSubmit, isSubmitting }: EditProjectModalProps) {
  const isMobileSheet = useIsMobileSheet();
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description ?? "");
  const [visibility, setVisibility] = useState<"public" | "private">(project.visibility);
  const [tags, setTags] = useState<string[]>(project.tags);

  const handleSubmit = async () => {
    await onSubmit({ name, description, visibility, tags });
  };

  return (
    <Sheet open onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <SheetContent side={isMobileSheet ? "bottom" : "right"} className="hub-sheet">
        <SheetHeader className="hub-sheet-header">
          <SheetTitle>Edit project</SheetTitle>
          <Button variant="ghost" className="hub-dialog-close" onClick={onClose}>
            ✕
          </Button>
        </SheetHeader>

        <SheetBody className="hub-dialog-scroll">
          <DialogBody className="hub-dialog-body">
            <div className="hub-form-row">
              <label className="hub-form-label">Project ID</label>
              <div className="hub-static-field">{project.project_id}</div>
            </div>

            <div className="hub-form-row">
              <label className="hub-form-label">Type</label>
              <Badge className={`hub-badge-${project.project_type}`}>{project.project_type}</Badge>
            </div>

            <div className="hub-form-row">
              <label className="hub-form-label">Display name</label>
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </div>

            <div className="hub-form-row">
              <label className="hub-form-label">Description</label>
              <Input value={description} onChange={(event) => setDescription(event.target.value)} />
            </div>

            <div className="hub-form-row">
              <label className="hub-form-label">Visibility</label>
              <VisibilitySelector value={visibility} onChange={setVisibility} />
            </div>

            <div className="hub-form-row">
              <label className="hub-form-label">Tags</label>
              <TagsInput tags={tags} onChange={setTags} suggestions={tagSuggestions} />
            </div>
          </DialogBody>
        </SheetBody>

        <SheetFooter>
          <DialogFooter className="hub-dialog-footer">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="default" onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
