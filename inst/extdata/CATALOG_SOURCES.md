# Indiana bird catalog sources

Snapshot built and verified: 2026-08-18.

## Indiana occurrence scope

- Source: Indiana Department of Natural Resources, Fish & Wildlife, **Birds of Indiana List**.
- URL: https://secure.in.gov/dnr/fish-and-wildlife/nongame-and-endangered-wildlife/birds/birds-of-indiana-list/
- Source statement: compiled by Indiana's state ornithologist using accepted taxonomic standards and other relevant information.
- Source revision shown: September 2021.
- Parsed rows: 424.

The packaged CSV includes every data row in that HTML table. The table includes two compound identification rows, so “424 records” should not be read as 424 independently recognized current species concepts.

## Taxonomy and range enrichment

- Source: Cornell Lab of Ornithology, eBird/Clements Checklist of Birds of the World v2025.
- Download page: https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2025/2025-citation-checklist-downloads/
- Release date shown: October 31, 2025.
- Matching rule: exact common-name match from each Indiana DNR row to a Cornell row whose category is `species`.
- Exact matches: 406 of 424.
- Unmatched DNR records: 18. These retain the DNR scientific name and receive an explicit unavailable-range note.

`brief_description` is generated locally from the DNR family group, the matched Cornell range statement when available, and the decoded DNR status. It is not copied prose from a species account.

## Known limitations

- The DNR occurrence table is revised September 2021 and may lag later Indiana Bird Records Committee decisions.
- The Indiana Audubon/IBRC site separately describes a 420-species official checklist; its scope and date are not assumed to be identical to the DNR table.
- Exact common-name matching deliberately avoids speculative joins after taxonomic name changes. Eighteen records therefore lack Cornell range enrichment.
- This dataset supports a personal app and conference demo. It should be refreshed and reviewed before scientific, regulatory, or conservation use.

The reproducible transformation is in `data-raw/build_species_seed.R`.
