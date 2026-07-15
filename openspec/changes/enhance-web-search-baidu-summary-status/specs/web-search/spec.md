## ADDED Requirements

### Requirement: WebSearchTool supports multi-source search
The system SHALL search both Bing and Baidu in parallel when `web_search` is invoked.

#### Scenario: Bing and Baidu both return results
- **WHEN** the Agent calls `web_search` with a query
- **THEN** the tool fetches results from both `https://cn.bing.com/search` and `https://www.baidu.com/s`
- **AND** the tool returns a merged list of results

#### Scenario: One search source fails
- **WHEN** the Bing request fails
- **THEN** the tool continues with Baidu results
- **AND** the final observation includes a note that only Baidu results were used

### Requirement: Search results are deduplicated
The system SHALL deduplicate results from both sources before ranking.

#### Scenario: Same page appears in Bing and Baidu
- **WHEN** both sources return a result pointing to the same canonical URL
- **THEN** the merged list contains only one entry for that URL

#### Scenario: Similar titles from different sources
- **WHEN** two results have titles with Jaccard similarity greater than 0.6
- **THEN** only the higher-ranked result is kept

### Requirement: Baidu results filter advertisements
The system SHALL exclude advertisement entries from Baidu results.

#### Scenario: Baidu result is marked as advertisement
- **WHEN** a Baidu result node contains `data-tuiguang`, class `ec_`, or the text “广告”/“推广”
- **THEN** that result is excluded from the merged list

#### Scenario: Advertisement domain appears in result link
- **WHEN** a result link matches the advertisement domain blacklist
- **THEN** that result is excluded from the merged list

### Requirement: Top results are fetched and summarized
The system SHALL fetch the full text of the top 3 merged results and generate a Chinese summary.

#### Scenario: Pages are reachable
- **WHEN** the top 3 result pages return valid HTML
- **THEN** the tool extracts main content from each page
- **AND** calls the LLM to produce a Chinese summary with source links

#### Scenario: Page fetch fails
- **WHEN** one of the top 3 pages fails or times out
- **THEN** the tool uses the search snippet for that page
- **AND** the summary is still generated from the available content

#### Scenario: LLM summary fails
- **WHEN** the LLM summary call fails
- **THEN** the tool returns the formatted raw search results
- **AND** the observation explains that summarization was unavailable

### Requirement: Search result format
The system SHALL include source links in the final observation.

#### Scenario: Summary is generated
- **WHEN** the summary is returned
- **THEN** the observation ends with a numbered list of source titles and URLs
