# Figure standards

Two passes, always in this order: **accurate** first, **readable** second. Aesthetics never buy back
inaccuracy — but an accurate figure nobody can parse has failed too.

Load this when producing or reviewing figures for a deliverable. A figure in an exploratory notebook
answers to the accuracy rules only.

**Boundary — one question only.** This reference governs whether a figure *supports the claim made
from it*: accuracy, axis honesty, declared *n* / error definition / test. How a figure is **rendered**
— backend choice, plotting code, palette libraries, themes, export mechanics, editable project files,
journal-template compliance — belongs to the figure toolchain, not here. The two **do not arbitrate
each other**: a figure can be beautifully styled and still fail this reference, and a figure can pass
this reference and then be restyled however the author likes.

## The block every figure carries

Regardless of figure type, four things must be answerable from the figure or its caption:

1. **One sentence** stating what the figure shows.
2. **n** — the number of units behind each mark, and what a unit is.
3. **Error definition** — SD, SEM, CI (and level), range, or explicitly *none*.
4. **Test** — which test produced any p-value or stars shown.

If the caption cannot state all four, the figure is not finished. "Error bars show mean ± SD" in a
figure legend for a 40-panel figure set is not enough; inconsistency between panels is the norm.

## Pass 1 — accuracy (must pass)

- **Every number in the figure exists in the result file.** Open both and compare. A figure
  regenerated from a stale intermediate is the most common invisible error.
- **The figure shows what the caption says it shows.** Re-read the caption against the plot. Axes
  swapped, groups renamed, or conditions reordered during iteration are all easy to miss.
- **The comparison shown is the comparison claimed.** If the text says "treated vs control", the
  figure must not be "treated vs vehicle" because that was the file that happened to exist.
- **Uncertainty is visible where it exists.** A point estimate without its interval is a claim of
  precision that has not been earned. When *n* is small, show the individual points.
- **Scale transformations are declared.** Log axis, normalization, and standardization must be named
  in the axis label or caption — not implied.
- **No silent axis truncation.** A bar chart whose y-axis starts at 95 exaggerates a 2% difference
  into a visual doubling. If a zoomed axis is genuinely needed, mark the break.
- **Colour and shape map to something real, and the mapping is in the legend.** No colour used purely
  for decoration, because readers will try to decode it.

## Axis honesty

| Don't | Why | Instead |
|---|---|---|
| Truncate a quantitative axis without a break marker | Amplifies differences arbitrarily | Start at zero, or mark the break explicitly |
| Dual y-axes for unrelated quantities | Any two series can be made to "correlate" by scaling | Two stacked panels sharing an x-axis |
| Area or 3D encoding for a magnitude | Human area perception is badly nonlinear | Length or position |
| Bar of means with no distribution | Hides bimodality, outliers, and small-n noise | Box/violin with points, or dot plot |
| Rainbow colormap for continuous data | Not perceptually uniform; creates false boundaries | A perceptually uniform map (viridis, magma, cividis) |
| Pie chart for more than ~3 categories | Angle comparison is unreliable | Sorted horizontal bar |
| Log axis applied silently | Changes the apparent effect size | Label the axis as log-scaled |

For diverging data (log fold changes, fold enrichment, z-scores), use a diverging map centred at
zero, and centre it at zero. A diverging scale with an off-centre midpoint invents a boundary.

## Colour

- **Perceptually uniform** for continuous scales; **colour-blind-safe** categorical palettes.
- **Never colour as the only channel.** Redundant encoding via shape, linetype, or direct labelling
  keeps the figure readable in greyscale — which is how a reviewer will print it.
- **Cap the category count.** Beyond about 8 colours, readers stop distinguishing and start guessing.
  Group the tail into "other", or facet.
- **Consistent meaning across the whole deliverable.** If blue is the treated group in figure 1, blue
  is the treated group in figure 6. Reusing a colour for a different meaning is worse than using a
  worse colour.
- **Check it at final size**, not on a large screen at 200% zoom.

## Layout and typography

- **One figure language.** Same font family, same base size, same palette, same legend conventions
  across every figure in a deliverable. Mixed styling reads as carelessness, and carelessness invites
  doubt about the parts the reader cannot check.
- **Legible at print size.** Minimum ~7 pt after final scaling; axis labels ~8–9 pt. Compute it from
  the final figure width, not from the on-screen preview.
- **Label every axis with quantity and unit.** "Expression" is not a label; "log2(counts+1)" is.
- **Panel letters** (A, B, C) in a consistent position, and referenced in the caption in order.
- **Whitespace is a design element.** Cramped panels read as noise. Group related panels; separate
  unrelated ones.
- **One language for text inside figures.** Journals and international venues are English; pick one
  language and apply it across the whole figure set. Don't mix within a panel.
- **Vector output** (PDF/SVG) for anything with text or lines; high-DPI raster only for images.
  Embed fonts so the typesetter's substitution doesn't shift your labels.

## The three-second test

Show the finished figure to someone who did not do the analysis. Ask: *what does this show?*

- **Answered in three seconds** → the figure works.
- **"I'd need you to explain it"** → the figure is carrying too much. Split it, simplify the encoding,
  or move detail to a supplement.
- **Answered wrongly** → the encoding is misleading, and this is an accuracy problem, not a taste
  problem. Fix the encoding, not the caption.

Then ask a second question: *what would you conclude from this?* If their conclusion is stronger than
your data supports — a trend read as an effect, an association read as a cause — the figure is
overclaiming, even if every number is right.

## Per-type must-haves

| Figure | Non-negotiable |
|---|---|
| Volcano plot | Thresholds drawn and labelled; axes named (log2FC, −log10 padj); use padj not p; genes labelled only if they are discussed |
| MA plot | Both axes named; the shrinkage/independent-filtering step stated if used |
| Heatmap | Clustering metric and linkage stated; scaled-by indicated (row/column/none); colour scale with units; sample annotation bar |
| PCA / UMAP / tSNE | Variance explained on PCs; for UMAP/tSNE, say it is not a distance metric; batch vs group annotation shown separately |
| Box / violin | n per box; whether points are shown; definition of the hinges or the violin kernel |
| Bar + error | The error definition, and the fact that n is behind it; whether it is mean or median |
| Enrichment (dot/bar) | Gene ratio or count on the x-axis stated; padj encoded and legended; database and version named |
| Phylogenetic tree | Support values shown; scale bar with units; outgroup or rooting stated |
| Alignment / coverage | Reference build named; depth axis; mapping quality filter stated |
| MD trajectory (RMSD/RMSF/Rg) | Equilibration region marked and excluded; the measured quantity named; replicas distinguished |
| Docking pose | Box definition; score and units; whether the pose is top-scoring or representative |
| Schematic figure | Every symbol meaning real biology; no invented arrows that imply unmeasured relationships |

## Anti-patterns

- **Stars without a test.** `***` means nothing unless the test and correction are stated.
- **"Representative image" without saying of what.** One field of view, selected by eye, is a curated
  claim. State the selection rule, or show the distribution.
- **Averages of categorical data.** A mean of a category code is not a quantity.
- **Dual-axis correlation.** Two unrelated trends on one panel "agree" because you chose the scales.
- **Dynamically ranged colour scales across panels.** A heatmap legend that rescales per panel makes
  panels visually incomparable while appearing comparable. Fix the range.
- **A cut panel that removes the awkward points.** If an outlier must be excluded, exclude it in the
  analysis with a stated rule, and say so — not by changing the plot window.
- **Reusing a figure from a different normalization.** Visually identical to the correct version.
  Check the `output` path in the provenance ledger against the one the figure actually read.

## Human review checklist

Hand this to the person reviewing figures. It is deliberately short — these are the items that catch
real errors.

- [ ] Every axis labelled with quantity and unit; scale transformation stated.
- [ ] n stated per panel; error definition stated and consistent.
- [ ] Test and multiple-testing correction named wherever significance is shown.
- [ ] Colours used consistently across the whole set, and readable in greyscale.
- [ ] No truncated quantitative axis without a marked break.
- [ ] The caption matches the data actually plotted (open the file and confirm).
- [ ] Text legible at final print size.
- [ ] The three-second test passes for a reader outside the analysis.
- [ ] The figure does not imply a stronger claim than the data supports.
