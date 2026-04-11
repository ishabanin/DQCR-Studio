import { forwardRef, type HTMLAttributes, type TableHTMLAttributes, type ThHTMLAttributes, type TdHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

const Table = forwardRef<HTMLTableElement, TableHTMLAttributes<HTMLTableElement>>(function Table({ className, ...props }, ref) {
  return <table ref={ref} className={cn("shad-table", className)} {...props} />;
});

const TableHead = forwardRef<HTMLTableSectionElement, HTMLAttributes<HTMLTableSectionElement>>(function TableHead({ className, ...props }, ref) {
  return <thead ref={ref} className={cn("shad-table-head", className)} {...props} />;
});

const TableBody = forwardRef<HTMLTableSectionElement, HTMLAttributes<HTMLTableSectionElement>>(function TableBody({ className, ...props }, ref) {
  return <tbody ref={ref} className={cn("shad-table-body", className)} {...props} />;
});

const TableRow = forwardRef<HTMLTableRowElement, HTMLAttributes<HTMLTableRowElement>>(function TableRow({ className, ...props }, ref) {
  return <tr ref={ref} className={cn("shad-table-row", className)} {...props} />;
});

const TableHeaderCell = forwardRef<HTMLTableCellElement, ThHTMLAttributes<HTMLTableCellElement>>(function TableHeaderCell(
  { className, ...props },
  ref,
) {
  return <th ref={ref} className={cn("shad-table-th", className)} {...props} />;
});

const TableCell = forwardRef<HTMLTableCellElement, TdHTMLAttributes<HTMLTableCellElement>>(function TableCell({ className, ...props }, ref) {
  return <td ref={ref} className={cn("shad-table-td", className)} {...props} />;
});

export { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell };
