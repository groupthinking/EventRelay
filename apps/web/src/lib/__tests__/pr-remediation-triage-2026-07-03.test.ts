import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

// This suite validates the internal consistency of the PR triage report
// docs/triage/pr-remediation-2026-07-03.md. The file is a generated triage
// artifact (not executable code), so the tests assert structural and
// cross-referential invariants: every PR number mentioned in prose is
// backed by a matrix row, the summary counts match the matrix contents,
// and the matrix table itself is well-formed.

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '../../../../..');
const docPath = join(repoRoot, 'docs/triage/pr-remediation-2026-07-03.md');
const content = readFileSync(docPath, 'utf8');

interface MatrixRow {
  pr: string;
  author: string;
  age: number;
  base: string;
  mergeable: string;
  terminal: string;
  command: string;
}

function extractSection(source: string, heading: string, nextHeading: string): string {
  const start = source.indexOf(heading);
  if (start === -1) {
    throw new Error(`Section heading not found: ${heading}`);
  }
  const from = start + heading.length;
  const end = source.indexOf(nextHeading, from);
  if (end === -1) {
    throw new Error(`Next heading not found after "${heading}": ${nextHeading}`);
  }
  return source.slice(from, end);
}

function parseMatrixRows(source: string): MatrixRow[] {
  const section = extractSection(source, '## Matrix (oldest first)', '## Owner-gated blockers');
  return section
    .split('\n')
    .filter((line) => /^\|\s*#\d+\s*\|/.test(line))
    .map((line) => {
      const cells = line
        .split('|')
        .slice(1, -1)
        .map((cell) => cell.trim());
      const [pr, author, age, base, mergeable, terminal, command] = cells;
      return {
        pr,
        author,
        age: Number(age),
        base,
        mergeable,
        terminal,
        command,
        cellCount: cells.length,
      } as MatrixRow & { cellCount: number };
    });
}

const rows = parseMatrixRows(content);

describe('PR remediation triage report 2026-07-03 (refresh)', () => {
  describe('document identity', () => {
    it('is titled as the refresh run for 2026-07-03', () => {
      expect(content).toMatch(/^# PR Remediation & Publish — run 2026-07-03 \(refresh\)/m);
    });

    it('declares 16 open PRs in the intro', () => {
      expect(content).toContain('all **16 open PRs**');
    });

    it('no longer claims the stale 14-PR count from the earlier same-day pass', () => {
      // Regression guard: the previous version of this file (superseded)
      // asserted 14 PRs; the refresh must not silently regress the count.
      expect(content).not.toMatch(/all \*\*14 open PRs\*\*/);
    });

    it('removed the now-obsolete "Corrections to the 2026-07-02 report" section', () => {
      expect(content).not.toContain('Corrections to the 2026-07-02 report');
    });

    it('records main at the updated commit 3214d64', () => {
      expect(content).toContain('`main` is now at `3214d64`');
    });
  });

  describe('required sections are present', () => {
    const requiredHeadings = [
      '## Headline',
      '## Terminal states (this run)',
      '## Matrix (oldest first)',
      '## Owner-gated blockers',
      '## Fast wins for the owner (no rebase, just a decision)',
      "## Answer to the loop's terminal question",
    ];

    it.each(requiredHeadings)('contains heading: %s', (heading) => {
      expect(content).toContain(heading);
    });
  });

  describe('matrix table structure', () => {
    it('parses exactly 16 data rows', () => {
      expect(rows).toHaveLength(16);
    });

    it('has a well-formed header matching the 7 documented columns', () => {
      expect(content).toContain(
        '| PR | Author | Age(d) | Base | mergeable | Terminal | Staged next command |'
      );
    });

    it('every row has exactly 7 cells (PR, Author, Age, Base, mergeable, Terminal, Command)', () => {
      for (const row of rows as (MatrixRow & { cellCount: number })[]) {
        expect(row.cellCount, `row ${row.pr} should have 7 cells`).toBe(7);
      }
    });

    it('every PR number is unique', () => {
      const prs = rows.map((r) => r.pr);
      expect(new Set(prs).size).toBe(prs.length);
    });

    it('lists PRs in oldest-first order (non-increasing age)', () => {
      const ages = rows.map((r) => r.age);
      for (let i = 1; i < ages.length; i++) {
        expect(ages[i], `age at index ${i} (${rows[i].pr}) should be <= previous`).toBeLessThanOrEqual(
          ages[i - 1]
        );
      }
    });

    it('every row terminal state is either DEFERRED(draft) or HALTED(<reason>)', () => {
      for (const row of rows) {
        expect(row.terminal).toMatch(/^(DEFERRED\(draft\)|HALTED\([a-z_]+\))$/);
      }
    });

    it('rows marked draft in the mergeable column use the DEFERRED(draft) terminal state', () => {
      for (const row of rows) {
        if (row.mergeable === 'draft') {
          expect(row.terminal).toBe('DEFERRED(draft)');
        } else {
          expect(row.terminal).not.toBe('DEFERRED(draft)');
        }
      }
    });

    it('includes all five newly opened PRs from today (age 0)', () => {
      const newPrs = rows.filter((r) => r.age === 0).map((r) => r.pr);
      expect(newPrs.sort()).toEqual(['#471', '#472', '#474', '#476', '#477'].sort());
    });
  });

  describe('terminal-state summary matches the matrix contents', () => {
    it('reports 5 DEFERRED(draft) rows matching the summary bullet', () => {
      const deferred = rows.filter((r) => r.terminal === 'DEFERRED(draft)');
      expect(deferred).toHaveLength(5);
      expect(content).toContain('**5** `DEFERRED(draft)` — #412, #415, #434, #442, #456');
      expect(deferred.map((r) => r.pr).sort()).toEqual(
        ['#412', '#415', '#434', '#442', '#456'].sort()
      );
    });

    it('reports 11 HALTED rows matching the summary bullet', () => {
      const halted = rows.filter((r) => r.terminal.startsWith('HALTED('));
      expect(halted).toHaveLength(11);
      expect(content).toContain('**11** `HALTED`:');
    });

    it('breaks down HALTED reasons exactly as merge_conflict / misdirected_base / blocked_required_check / redundant', () => {
      const byReason = (reason: string) =>
        rows.filter((r) => r.terminal === `HALTED(${reason})`).map((r) => r.pr).sort();

      expect(byReason('merge_conflict')).toEqual(
        ['#327', '#328', '#365', '#414', '#433', '#436', '#474'].sort()
      );
      expect(byReason('misdirected_base')).toEqual(['#471', '#476'].sort());
      expect(byReason('blocked_required_check')).toEqual(['#472']);
      expect(byReason('redundant')).toEqual(['#477']);
    });

    it('DEFERRED + HALTED counts sum to the total open PR count (16)', () => {
      const deferred = rows.filter((r) => r.terminal === 'DEFERRED(draft)').length;
      const halted = rows.filter((r) => r.terminal.startsWith('HALTED(')).length;
      expect(deferred + halted).toBe(16);
    });
  });

  describe('cross-references between prose and matrix', () => {
    it('the Headline flags #477 as redundant, matching its matrix terminal state', () => {
      const headlineSection = extractSection(content, '## Headline', '## Terminal states');
      expect(headlineSection).toContain('#477 re-proposes the same commit');
      expect(headlineSection).toContain('**redundant → recommend close**');
      const row = rows.find((r) => r.pr === '#477');
      expect(row?.terminal).toBe('HALTED(redundant)');
    });

    it('the Headline does not claim any PR was merged by this run, consistent with the "0 MERGED" summary', () => {
      const headlineSection = extractSection(content, '## Headline', '## Terminal states');
      expect(headlineSection).toContain('No PR was merged by this run, and none could be.');
      expect(content).toContain('**0** `MERGED` by this run.');
    });

    it('every PR referenced in "Fast wins for the owner" exists in the matrix and is not draft-deferred', () => {
      const fastWins = extractSection(
        content,
        '## Fast wins for the owner (no rebase, just a decision)',
        "## Answer to the loop's terminal question"
      );
      const referenced = [...new Set([...fastWins.matchAll(/#(\d+)/g)].map((m) => `#${m[1]}`))];
      expect(referenced.sort()).toEqual(['#433', '#471', '#476', '#477'].sort());

      const byPr = new Map(rows.map((r) => [r.pr, r]));
      for (const pr of referenced) {
        const row = byPr.get(pr);
        expect(row, `${pr} should be present in the matrix`).toBeDefined();
        expect(row!.terminal.startsWith('HALTED(')).toBe(true);
      }
    });

    it('the closing "Answer to the loop\'s terminal question" cites the same close-decision PRs as Fast wins', () => {
      const idx = content.indexOf("## Answer to the loop's terminal question");
      expect(idx).toBeGreaterThan(-1);
      const closingSection = content.slice(idx);
      const referenced = [
        ...new Set([...closingSection.matchAll(/#(\d+)/g)].map((m) => `#${m[1]}`)),
      ];
      expect(referenced.sort()).toEqual(['#433', '#471', '#476', '#477'].sort());
    });

    it('the "5 new PRs opened today" callout matches the age-0 matrix rows', () => {
      expect(content).toContain(
        'five new PRs\nopened today (**#471, #472, #474, #476, #477**)'
      );
      const newPrs = rows.filter((r) => r.age === 0).map((r) => r.pr).sort();
      expect(newPrs).toEqual(['#471', '#472', '#474', '#476', '#477'].sort());
    });
  });

  describe('owner-gated blockers section', () => {
    it('enumerates exactly 3 numbered blockers', () => {
      const section = extractSection(
        content,
        '## Owner-gated blockers',
        '## Fast wins for the owner (no rebase, just a decision)'
      );
      const numbered = section.match(/^\d+\.\s/gm) ?? [];
      expect(numbered).toHaveLength(3);
    });

    it('states no automerge labels exist on protected main', () => {
      expect(content).toContain('No `automerge` labels on protected `main`');
    });
  });
});