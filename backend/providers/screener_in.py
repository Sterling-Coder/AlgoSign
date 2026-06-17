import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ScreenerFundamentalData:
    def __init__(self):
        # Multiple URL formats to try
        self.base_urls = [
            "https://www.screener.in/company/{}/",  # Base URL (often has data)
            "https://www.screener.in/company/{}/consolidated/",  # Consolidated view
            "https://www.screener.in/company/{}/standalone/",  # Standalone view
        ]
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.timeout = 20
    
    def _has_meaningful_data(self, soup: BeautifulSoup) -> bool:
        """
        Check if the page contains meaningful data (not just empty placeholders)
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            True if page has meaningful data, False otherwise
        """
        # Check for company name
        h1 = soup.find('h1', class_='h2')
        if not h1:
            return False
        
        # Check for top ratios with actual values
        top_ratios = soup.find('ul', {'id': 'top-ratios'})
        if top_ratios:
            items = top_ratios.find_all('li')
            for item in items:
                name_span = item.find('span', class_='name')
                number_span = item.find('span', class_='number')
                if name_span and number_span:
                    value = number_span.get_text(strip=True)
                    # If we find at least one non-empty value, consider it meaningful
                    if value and value not in ['', '-', 'N/A', 'N/A%']:
                        return True
        
        # Check for tables with actual data
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:  # Has data rows beyond header
                first_data_row = rows[1] if len(rows) > 1 else None
                if first_data_row:
                    cells = first_data_row.find_all(['td', 'th'])
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        # Check if cell has meaningful data (numbers, percentages, etc.)
                        if text and text not in ['', '-', 'N/A'] and (
                            re.search(r'\d', text) or  # Contains numbers
                            '%' in text or  # Contains percentages
                            '₹' in text or  # Contains currency
                            'Cr' in text or 'L' in text  # Contains financial units
                        ):
                            return True
        
        return False
    
    def fetch_all_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive fundamental data for a given stock symbol
        
        Args:
            symbol: Stock symbol (e.g., 'TCS', 'RELIANCE')
            
        Returns:
            Dictionary containing all fundamental data or None if failed
        """
        soup = None
        successful_url = None
        
        # Try multiple URL formats
        for url_template in self.base_urls:
            url = url_template.format(symbol)
            try:
                response = self.session.get(url, headers=self.headers, timeout=self.timeout)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check if this URL has actual data (not just empty placeholders)
                    if self._has_meaningful_data(soup):
                        successful_url = url
                        logger.info(f"Successfully loaded data from: {url}")
                        break
                    else:
                        logger.warning(f"URL {url} loaded but has no meaningful data")
                else:
                    logger.warning(f"URL {url} returned status {response.status_code}")
            except Exception as e:
                logger.warning(f"Failed to fetch from {url}: {e}")
                continue
        
        if soup is None:
            logger.error(f"Failed to fetch data for {symbol} from any URL")
            return None
        
        try:
            # Extract all data sections
            peers_data = self._extract_peers(soup)
            peers_comparison_data = self._extract_peer_comparison(soup)
            
            # Try to fetch additional peer data from API endpoints
            api_peers = self._fetch_peers_from_api(symbol)
            if api_peers:
                peers_data.extend(api_peers)
            
            # Log extracted data for debugging
            logger.info(f"Peers data extracted: {len(peers_data)} records")
            logger.info(f"Peers comparison data extracted: {len(peers_comparison_data)} records")

            # Extract shareholding data and create yearly aggregation
            shareholding_quarterly = self._extract_shareholding(soup)
            shareholding_yearly = self._aggregate_shareholding_yearly(shareholding_quarterly)

            # Extract basic data
            company_info = self._extract_company_info(soup)
            price_data = self._extract_price_data(soup)
            key_metrics = self._extract_key_metrics(soup)
            
            # If we don't have enough data, try API fallback
            if not company_info or len([v for v in company_info.values() if v]) < 3:
                api_data = self._fetch_company_data_from_api(symbol)
                if api_data:
                    # Merge API data with extracted data
                    for key, value in api_data.items():
                        if key not in company_info or not company_info[key]:
                            company_info[key] = str(value) if value else ''

            data = {
                'symbol': symbol.upper(),
                'url': successful_url,
                'fetch_timestamp': datetime.now().isoformat(),
                'company_info': company_info,
                'price_data': price_data,
                'key_metrics': key_metrics,
                'shareholding': shareholding_quarterly,
                'shareholding_yearly': shareholding_yearly,
                'quarterly_results': self._extract_quarterly_results(soup),
                'profit_loss': self._extract_profit_loss(soup),
                'balance_sheet': self._extract_balance_sheet(soup),
                'cash_flow': self._extract_cash_flow(soup),
                'ratios': self._extract_ratios(soup),
                'peers': peers_data,
                'about': self._extract_about_info(soup),
                'pros_cons': self._extract_pros_cons(soup),
                'peers_comparison': peers_comparison_data,
                'documents': self._extract_documents(soup),
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract basic company information and top ratios with enhanced fallback methods"""
        info = {}
        
        # Company name - try multiple selectors
        company_name_selectors = [
            'h1.h2',
            'h1',
            '.company-name',
            '.stock-name',
            '[class*="company"] h1',
            '[class*="stock"] h1'
        ]
        
        for selector in company_name_selectors:
            element = soup.select_one(selector)
            if element:
                info['name'] = element.get_text(strip=True)
                break
        
        # Top ratios section - try multiple approaches
        top_ratios_selectors = [
            'ul#top-ratios',
            '.top-ratios',
            '[class*="top-ratios"]',
            '.ratios',
            '[class*="ratios"]'
        ]
        
        top_ratios = None
        for selector in top_ratios_selectors:
            top_ratios = soup.select_one(selector)
            if top_ratios:
                break
        
        if top_ratios:
            items = top_ratios.find_all('li')
            for item in items:
                # Try different span class combinations
                name_selectors = [
                    'span.name',
                    'span.label',
                    '.name',
                    '.label',
                    'span[class*="name"]',
                    'span[class*="label"]'
                ]
                
                number_selectors = [
                    'span.number',
                    'span.value',
                    '.number',
                    '.value',
                    'span[class*="number"]',
                    'span[class*="value"]'
                ]
                
                name_span = None
                number_span = None
                
                for name_sel in name_selectors:
                    name_span = item.select_one(name_sel)
                    if name_span:
                        break
                
                for num_sel in number_selectors:
                    number_span = item.select_one(num_sel)
                    if number_span:
                        break
                
                if name_span and number_span:
                    key = name_span.get_text(strip=True)
                    value = number_span.get_text(strip=True)
                    if key and value:
                        info[key] = value
        
        # Fallback: Look for ratios in other sections
        if not info or len([v for v in info.values() if v]) < 3:
            self._extract_ratios_from_sections(soup, info)
        
        # Fallback: Look for ratios in script tags
        if not info or len([v for v in info.values() if v]) < 3:
            self._extract_ratios_from_scripts(soup, info)
        
        return info
    
    def _extract_ratios_from_sections(self, soup: BeautifulSoup, info: Dict[str, str]) -> None:
        """Extract ratios from various sections as fallback"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if not heading:
                continue
            
            # Look for ratio-like data in this section
            items = section.find_all('li')
            for item in items:
                text = item.get_text(strip=True)
                # Look for patterns like "Market Cap: 5,944" or "P/E: 15.2"
                ratio_match = re.search(r'([^:]+):\s*([^\s]+)', text)
                if ratio_match:
                    key = ratio_match.group(1).strip()
                    value = ratio_match.group(2).strip()
                    if key and value and value not in ['', '-', 'N/A']:
                        info[key] = value
    
    def _extract_ratios_from_scripts(self, soup: BeautifulSoup, info: Dict[str, str]) -> None:
        """Extract ratios from script tags as fallback"""
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string and len(script.string) > 100:
                script_text = script.string
                
                # Look for JSON data containing ratios
                try:
                    # Try to find JSON objects with ratio data
                    json_patterns = [
                        r'ratios["\']?\s*:\s*(\{[^}]+\})',
                        r'company["\']?\s*:\s*(\{[^}]+\})',
                        r'data["\']?\s*:\s*(\{[^}]+\})'
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.findall(pattern, script_text, re.DOTALL)
                        for match in matches:
                            try:
                                data = json.loads(match)
                                if isinstance(data, dict):
                                    for key, value in data.items():
                                        if isinstance(value, (str, int, float)) and str(value) not in ['', '-', 'N/A']:
                                            info[key] = str(value)
                            except json.JSONDecodeError:
                                continue
                            except Exception:
                                continue
                except Exception:
                    continue

    def _extract_price_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract current price and related price metrics"""
        price_data = {}
        
        # Current stock price
        current_price = soup.find('span', {'id': 'stock-price'})
        if current_price:
            price_data['current_price'] = current_price.get_text(strip=True)
        
        # Price warehouse data
        warehouse = soup.find('div', {'id': 'stock-price'})
        if warehouse:
            spans = warehouse.find_all('span', class_='number')
            for span in spans:
                parent = span.parent
                if parent:
                    label = parent.find('small')
                    if label:
                        key = label.get_text(strip=True)
                        value = span.get_text(strip=True)
                        price_data[key] = value
        
        return price_data

    def _extract_key_metrics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract key financial metrics from all sections"""
        metrics = {}
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if not heading:
                continue
            
            items = section.find_all('li')
            
            for item in items:
                name = item.find('span', class_='name')
                number = item.find('span', class_='number')
                if name and number:
                    metrics[name.get_text(strip=True)] = number.get_text(strip=True)
        
        return metrics

    def _extract_shareholding(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract shareholding pattern data"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and 'shareholding' in heading.get_text().lower():
                table = section.find('table')
                if table:
                    return self._parse_table(table)
        
        return []

    def _extract_quarterly_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract quarterly results data"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and 'quarter' in heading.get_text().lower():
                table = section.find('table')
                if table:
                    return self._parse_table(table)
        
        return []

    def _extract_profit_loss(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract profit & loss statement data"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and 'profit' in heading.get_text().lower():
                table = section.find('table')
                if table:
                    return self._parse_table(table)
        
        return []

    def _extract_balance_sheet(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract balance sheet data"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and 'balance' in heading.get_text().lower():
                table = section.find('table')
                if table:
                    return self._parse_table(table)
        
        return []

    def _extract_cash_flow(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract cash flow statement data"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and 'cash' in heading.get_text().lower():
                table = section.find('table')
                if table:
                    return self._parse_table(table)
        
        return []

    def _extract_ratios(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract financial ratios data"""
        sections = soup.find_all('section')
        
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and 'ratio' in heading.get_text().lower():
                table = section.find('table')
                if table:
                    return self._parse_table(table)
        
        return []

    def _extract_peers(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract peer companies data"""
        peers_data = []
        
        # Look for peer sections with various possible class names and IDs
        peer_selectors = [
            'section[id*="peer"]',
            'div[id*="peer"]', 
            'section[class*="peer"]',
            'div[class*="peer"]',
            'section[class*="competitor"]',
            'div[class*="competitor"]'
        ]
        
        for selector in peer_selectors:
            sections = soup.select(selector)
            for section in sections:
                table = section.find('table')
                if table:
                    peers_data.extend(self._parse_table(table))
        
        # Also check for peer data in general sections
        sections = soup.find_all('section')
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and ('peer' in heading.get_text().lower() or 'competitor' in heading.get_text().lower()):
                table = section.find('table')
                if table:
                    peers_data.extend(self._parse_table(table))
        
        # Fallback: Look for any table that might contain peer data
        if not peers_data:
            all_tables = soup.find_all('table')
            for table in all_tables:
                # Check if table contains peer-related data
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['peer', 'competitor', 'similar', 'compare']):
                    peers_data.extend(self._parse_table(table))
                    break
        
        return peers_data

    def _extract_about_info(self, soup: BeautifulSoup) -> Dict[str, Union[str, List[str]]]:
        """Extract company about/description information"""
        about = {}

        # Try profile/about sections (multiple common layouts)
        candidates = [
            soup.find('div', class_='profile'),
            soup.find('div', class_='about-section'),
            soup.find('section', id='about'),
        ]
        
        for panel in candidates:
            if panel:
                # Description (found in p, div, or span)
                desc = panel.find(['p', 'div', 'span'])
                if desc:
                    about['description'] = desc.get_text(strip=True)

                # Key Points (found in ul/li or div)
                kp = panel.find('ul', class_='key-points') or panel.find('div', class_='key-points')
                if kp:
                    points = [li.get_text(strip=True) for li in kp.find_all('li')]
                    about['key_points'] = points if points else kp.get_text(separator=" | ", strip=True)

        # Fallback to meta tag if description not found
        if not about.get('description'):
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc:
                about['meta_description'] = meta_desc.get('content', '')

        return about

    def _extract_pros_cons(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract pros and cons analysis with enhanced detection"""
        data = {'pros': [], 'cons': []}
        
        # Look for pros and cons in multiple possible locations
        pros_cons_selectors = [
            # Direct ID/class selectors
            'div[id="pros"]', 'div[id="cons"]',
            'ul[class*="pros"]', 'ul[class*="cons"]',
            'div[class*="pros"]', 'div[class*="cons"]',
            'section[id*="pros"]', 'section[id*="cons"]',
            # More generic selectors
            'div[class*="advantage"]', 'div[class*="disadvantage"]',
            'div[class*="strength"]', 'div[class*="weakness"]',
            'div[class*="positive"]', 'div[class*="negative"]'
        ]
        
        for selector in pros_cons_selectors:
            elements = soup.select(selector)
            for element in elements:
                # Check if this is a pros or cons section
                element_text = element.get_text().lower()
                element_id = element.get('id', '').lower()
                element_class = ' '.join(element.get('class', [])).lower()
                
                is_pros = any(keyword in element_text or keyword in element_id or keyword in element_class 
                             for keyword in ['pros', 'advantage', 'strength', 'positive', 'benefit'])
                is_cons = any(keyword in element_text or keyword in element_id or keyword in element_class 
                             for keyword in ['cons', 'disadvantage', 'weakness', 'negative', 'risk'])
                
                if is_pros or is_cons:
                    # Extract list items
                    list_items = element.find_all('li')
                    if list_items:
                        items = [li.get_text(strip=True) for li in list_items if li.get_text(strip=True)]
                        if is_pros:
                            data['pros'].extend(items)
                        else:
                            data['cons'].extend(items)
                    else:
                        # If no list items, try to extract text from divs/spans
                        text_items = element.find_all(['div', 'span', 'p'])
                        items = [item.get_text(strip=True) for item in text_items if item.get_text(strip=True) and len(item.get_text(strip=True)) > 10]
                        if is_pros:
                            data['pros'].extend(items)
                        else:
                            data['cons'].extend(items)
        
        # Look for pros/cons in sections with specific headings
        sections = soup.find_all('section')
        for section in sections:
            heading = section.find(['h2', 'h3', 'h4'])
            if heading:
                heading_text = heading.get_text().lower()
                if any(keyword in heading_text for keyword in ['pros', 'cons', 'advantages', 'disadvantages', 'strengths', 'weaknesses']):
                    list_items = section.find_all('li')
                    if list_items:
                        items = [li.get_text(strip=True) for li in list_items if li.get_text(strip=True)]
                        if 'pros' in heading_text or 'advantage' in heading_text or 'strength' in heading_text:
                            data['pros'].extend(items)
                        elif 'cons' in heading_text or 'disadvantage' in heading_text or 'weakness' in heading_text:
                            data['cons'].extend(items)
        
        # Look for pros/cons in script tags (often loaded via JavaScript)
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and ('pros' in script.string.lower() or 'cons' in script.string.lower()):
                try:
                    # Look for JSON data containing pros/cons
                    pros_match = re.search(r'pros["\']?\s*:\s*(\[.*?\])', script.string, re.DOTALL)
                    cons_match = re.search(r'cons["\']?\s*:\s*(\[.*?\])', script.string, re.DOTALL)
                    
                    if pros_match:
                        pros_json = json.loads(pros_match.group(1))
                        if isinstance(pros_json, list):
                            data['pros'].extend([str(item) for item in pros_json])
                    
                    if cons_match:
                        cons_json = json.loads(cons_match.group(1))
                        if isinstance(cons_json, list):
                            data['cons'].extend([str(item) for item in cons_json])
                except:
                    pass
        
        # Look for pros/cons in data attributes or hidden elements
        data_elements = soup.find_all(attrs={'data-pros': True}) + soup.find_all(attrs={'data-cons': True})
        for element in data_elements:
            if element.get('data-pros'):
                data['pros'].append(element.get('data-pros'))
            if element.get('data-cons'):
                data['cons'].append(element.get('data-cons'))
        
        # Look for pros/cons in meta tags
        meta_pros = soup.find('meta', {'name': 'pros'})
        meta_cons = soup.find('meta', {'name': 'cons'})
        if meta_pros and meta_pros.get('content'):
            data['pros'].append(meta_pros.get('content'))
        if meta_cons and meta_cons.get('content'):
            data['cons'].append(meta_cons.get('content'))
        
        # Look for pros/cons in comments (sometimes data is in HTML comments)
        comments = soup.find_all(string=lambda text: isinstance(text, str) and ('pros' in text.lower() or 'cons' in text.lower()))
        for comment in comments:
            if 'pros' in comment.lower():
                # Extract pros from comment
                pros_items = re.findall(r'pros?["\']?\s*:\s*["\']?([^"\']+)["\']?', comment, re.IGNORECASE)
                data['pros'].extend(pros_items)
            if 'cons' in comment.lower():
                # Extract cons from comment
                cons_items = re.findall(r'cons?["\']?\s*:\s*["\']?([^"\']+)["\']?', comment, re.IGNORECASE)
                data['cons'].extend(cons_items)
        
        # Try to fetch pros/cons from API if not found in HTML
        if not data['pros'] and not data['cons']:
            api_pros_cons = self._fetch_pros_cons_from_api(soup)
            if api_pros_cons:
                data['pros'].extend(api_pros_cons.get('pros', []))
                data['cons'].extend(api_pros_cons.get('cons', []))
        
        # Remove duplicates and empty strings
        data['pros'] = list(set([item for item in data['pros'] if item.strip()]))
        data['cons'] = list(set([item for item in data['cons'] if item.strip()]))
        
        logger.info(f"Extracted {len(data['pros'])} pros and {len(data['cons'])} cons")
        return data

    def _extract_peer_comparison(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract peer comparison data"""
        comparison_data = []
        
        # Look for peer comparison sections with various possible selectors
        comparison_selectors = [
            'section[id*="comparison"]',
            'div[id*="comparison"]',
            'section[class*="comparison"]',
            'div[class*="comparison"]',
            'section[id="peers"]',
            'div[id="peers"]',
            'div[class*="peer-comparison"]',
            'table[class*="peer"]',
            'table[class*="comparison"]'
        ]
        
        for selector in comparison_selectors:
            elements = soup.select(selector)
            for element in elements:
                table = element.find('table') if element.name != 'table' else element
                if table:
                    comparison_data.extend(self._parse_table(table))
        
        # Also check for comparison data in general sections
        sections = soup.find_all('section')
        for section in sections:
            heading = section.find(['h2', 'h3'])
            if heading and ('comparison' in heading.get_text().lower() or 'vs' in heading.get_text().lower()):
                table = section.find('table')
                if table:
                    comparison_data.extend(self._parse_table(table))
        
        # Fallback: Look for any table that might contain comparison data
        if not comparison_data:
            all_tables = soup.find_all('table')
            for table in all_tables:
                # Check if table contains comparison-related data
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['vs', 'versus', 'compare', 'comparison', 'peer']):
                    comparison_data.extend(self._parse_table(table))
                    break
        
        return comparison_data

    def _extract_documents(self, soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
        """Extract documents and announcements with proper categorization"""
        docs = {
            'recent_announcements': [],
            'important_announcements': [],
            'annual_reports': [],
            'credit_ratings': []
        }

        # Extract announcements from Recent and Important tabs separately
        recent_announcements, important_announcements = self._extract_recent_important_announcements(soup)
        docs['recent_announcements'] = recent_announcements
        docs['important_announcements'] = important_announcements
        
        # Extract other documents
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            txt = link.get_text(strip=True)
            href = link['href']
            
            # Skip empty or very short text
            if not txt or len(txt) < 3:
                continue
            
            # Categorize based on text content
            txt_lower = txt.lower()
            
            # Annual Reports - more specific patterns
            if any(pattern in txt_lower for pattern in [
                'financial year', 'annual report', 'ar_', 'annualreport',
                'fy20', 'fy21', 'fy22', 'fy23', 'fy24', 'fy25',
                'year 202', 'year 201', 'year 2020', 'year 2021', 
                'year 2022', 'year 2023', 'year 2024', 'year 2025'
            ]):
                # Additional check to ensure it's actually an annual report
                if any(keyword in txt_lower for keyword in ['bse', 'nse', 'pdf', 'zip']) or 'from bse' in txt_lower or 'from nse' in txt_lower:
                    docs['annual_reports'].append({'label': txt, 'url': href})

            # Credit Ratings
            elif any(pattern in txt_lower for pattern in [
                'rating', 'crisil', 'icra', 'care', 'fitch', 'moody', 's&p'
            ]):
                    docs['credit_ratings'].append({'label': txt, 'url': href})

        # Remove duplicates while preserving order
        for category in docs:
            seen = set()
            unique_docs = []
            for doc in docs[category]:
                doc_key = (doc['label'], doc['url'])
                if doc_key not in seen:
                    seen.add(doc_key)
                    unique_docs.append(doc)
            docs[category] = unique_docs

        logger.info(f"Extracted documents - Annual Reports: {len(docs['annual_reports'])}, "
                   f"Credit Ratings: {len(docs['credit_ratings'])}, "
                   f"Recent Announcements: {len(docs['recent_announcements'])}, "
                   f"Important Announcements: {len(docs['important_announcements'])}")

        return docs

    def _extract_recent_important_announcements(self, soup: BeautifulSoup) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Extract announcements from Recent and Important tabs separately"""
        recent_announcements = []
        important_announcements = []
        
        # Method 1: Look for announcements section with tabs
        announcements_section = None
        
        # Try multiple selectors for announcements section
        for selector in [
            'section[id="documents"]',
            'div.announcements',
            'div[class*="announcement"]',
            'section[class*="announcement"]',
            'div[class*="document"]',
            'section[class*="document"]'
        ]:
            announcements_section = soup.select_one(selector)
            if announcements_section:
                break
        
        # Method 2: Look for any section containing "Announcements" heading
        if not announcements_section:
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                if 'announcement' in heading.get_text().lower():
                    announcements_section = heading.find_parent(['section', 'div'])
                    if announcements_section:
                        break
        
        if announcements_section:
            # Look for both Recent and Important tab content specifically
            self._extract_from_tab_sections(announcements_section, recent_announcements, important_announcements)
            
            # Also look for announcement items directly in the section (fallback)
            self._extract_announcements_from_container(announcements_section, recent_announcements, important_announcements)
        
        # Method 3: Look for announcements in script tags (often loaded dynamically)
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and ('announcement' in script.string.lower() or 'recent' in script.string.lower() or 'important' in script.string.lower()):
                self._extract_announcements_from_script(script, recent_announcements, important_announcements)
        
        # Method 4: Look for announcements in all links (fallback)
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            txt = link.get_text(strip=True)
            href = link['href']
            
            if (txt and len(txt) > 20 and any(keyword in txt.lower() for keyword in [
                'announcement', 'disclosure', 'intimation', 'update', 'closure',
                'meeting', 'amalgamation', 'dissolution', 'regulation', 'sebi',
                'lodr', 'upsi', 'institutional', 'investor', 'summit', 'effective',
                'subsidiary', 'wholly-owned', 'participation', 'trading window',
                'press release', 'corporate action', 'board', 'dividend',
                'partnership', 'collaboration', 'transformation', 'deal',
                'migration', 'modernise', 'ai-powered', 'digital transformation',
                'vodafone', 'warehouse group', 'odisha', 'tryg', 'lloyds', 'scottish widows'
            ]) and not any(skip_word in txt.lower() for skip_word in [
                'company announcementsstay', 'stay updated', 'search, filter', 'nifty', 'bse',
                'rating update', 'from icra', 'from crisil', 'from care', 'from fitch'
            ])):
                # Categorize based on content
                if any(keyword in txt.lower() for keyword in [
                    'press release', 'partnership', 'collaboration', 'transformation', 'deal',
                    'migration', 'modernise', 'ai-powered', 'digital transformation',
                    'vodafone', 'warehouse group', 'odisha', 'tryg', 'lloyds', 'scottish widows'
                ]):
                    important_announcements.append({
                        'label': txt,
                        'url': href,
                        'date': ''
                    })
                else:
                    recent_announcements.append({
                        'label': txt,
                        'url': href,
                        'date': ''
                    })
        
        # Remove duplicates
        recent_announcements = self._remove_duplicates(recent_announcements)
        important_announcements = self._remove_duplicates(important_announcements)
        
        logger.info(f"Extracted {len(recent_announcements)} recent and {len(important_announcements)} important announcements")
        return recent_announcements, important_announcements

    def _remove_duplicates(self, announcements):
        """Remove duplicate announcements while preserving order"""
        seen = set()
        unique_announcements = []
        for announcement in announcements:
            key = (announcement['label'], announcement['url'])
            if key not in seen:
                seen.add(key)
                unique_announcements.append(announcement)
        return unique_announcements

    def _extract_from_tab_sections(self, announcements_section, recent_announcements, important_announcements):
        """Extract announcements from Recent and Important tab sections specifically"""
        # Look for tab buttons to identify the structure
        # tab_buttons = announcements_section.find_all(['button', 'a', 'div'], class_=re.compile(r'(tab|nav)', re.I))
        
        # Look for tab content areas
        tab_content_areas = announcements_section.find_all(['div', 'section'], class_=re.compile(r'(tab-content|tabpanel|content)', re.I))
        
        # If we find tab content areas, extract from them
        if tab_content_areas:
            for tab_area in tab_content_areas:
                # Check if this tab area contains Recent or Important content
                tab_text = tab_area.get_text().lower()
                if 'recent' in tab_text or 'important' in tab_text or 'press release' in tab_text:
                    self._extract_announcements_from_container(tab_area, recent_announcements, important_announcements)
        
        # Also look for specific data attributes or IDs that might indicate Recent/Important tabs
        recent_tab = announcements_section.find(['div', 'section'], {'data-tab': 'recent'}) or \
                    announcements_section.find(['div', 'section'], {'id': 'recent'}) or \
                    announcements_section.find(['div', 'section'], class_=re.compile(r'recent', re.I))
        
        important_tab = announcements_section.find(['div', 'section'], {'data-tab': 'important'}) or \
                       announcements_section.find(['div', 'section'], {'id': 'important'}) or \
                       announcements_section.find(['div', 'section'], class_=re.compile(r'important', re.I))
        
        if recent_tab:
            self._extract_announcements_from_container(recent_tab, recent_announcements, important_announcements)
        
        if important_tab:
            self._extract_announcements_from_container(important_tab, recent_announcements, important_announcements)
        
        # Look for press releases and important announcements by content patterns
        all_items = announcements_section.find_all(['div', 'li', 'article'])
        for item in all_items:
            item_text = item.get_text().lower()
            # Look for press releases and important business announcements
            if any(keyword in item_text for keyword in [
                'press release', 'partnership', 'collaboration', 'transformation', 'deal',
                'migration', 'modernise', 'ai-powered', 'digital transformation',
                'vodafone', 'warehouse group', 'odisha', 'tryg', 'lloyds', 'scottish widows',
                'bss transformation', 'it transformation', 'financial management system',
                'policy migration', 'portfolio migration', 'workbench'
            ]):
                self._extract_announcements_from_container(item, recent_announcements, important_announcements)
        
        # Also search the entire page for press releases and important announcements
        all_divs = announcements_section.find_all(['div', 'span', 'p'])
        for div in all_divs:
            div_text = div.get_text().strip()
            if (len(div_text) > 30 and any(keyword in div_text.lower() for keyword in [
                'press release', 'partnership', 'collaboration', 'transformation', 'deal',
                'migration', 'modernise', 'ai-powered', 'digital transformation',
                'vodafone', 'warehouse group', 'odisha', 'tryg', 'lloyds', 'scottish widows'
            ]) and not any(skip_word in div_text.lower() for skip_word in [
                'company announcementsstay', 'stay updated', 'search, filter', 'nifty', 'bse',
                'rating update', 'from icra', 'from crisil', 'from care', 'from fitch'
            ])):
                # Check if this div contains a link
                link = div.find('a', href=True)
                if link:
                    important_announcements.append({
                        'label': div_text,
                        'url': link['href'],
                        'date': ''
                    })

    def _extract_announcements_from_container(self, container, recent_announcements, important_announcements):
        """Extract announcements from a specific container"""
        # Look for announcement items
        items = container.find_all(['div', 'li', 'article'], class_=re.compile(r'(announcement|item|entry|card)', re.I))
        
        for item in items:
            # Extract title and date
            title_elem = item.find(['a', 'span', 'div'], class_=re.compile(r'(title|heading|name|label)', re.I))
            date_elem = item.find(['span', 'div', 'time'], class_=re.compile(r'(date|time|created)', re.I))
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '') if title_elem.name == 'a' else ''
                date = date_elem.get_text(strip=True) if date_elem else ''
                
                # Filter for actual announcements (exclude navigation and rating updates)
                if (any(keyword in title.lower() for keyword in [
                    'announcement', 'disclosure', 'intimation', 'update', 'closure',
                    'meeting', 'amalgamation', 'dissolution', 'regulation', 'sebi',
                    'lodr', 'upsi', 'institutional', 'investor', 'summit', 'effective',
                    'subsidiary', 'wholly-owned', 'participation', 'trading window',
                    'press release', 'corporate action', 'board', 'dividend'
                ]) and not any(skip_word in title.lower() for skip_word in [
                    'company announcementsstay', 'stay updated', 'search, filter', 'nifty', 'bse',
                    'rating update', 'from icra', 'from crisil', 'from care', 'from fitch'
                ]) and len(title) > 20):
                    # Categorize based on content
                    if any(keyword in title.lower() for keyword in [
                        'press release', 'partnership', 'collaboration', 'transformation', 'deal',
                        'migration', 'modernise', 'ai-powered', 'digital transformation',
                        'vodafone', 'warehouse group', 'odisha', 'tryg', 'lloyds', 'scottish widows'
                    ]):
                        important_announcements.append({
                            'label': title,
                            'url': href,
                            'date': date
                        })
                    else:
                        recent_announcements.append({
                            'label': title,
                            'url': href,
                            'date': date
                        })

    def _extract_announcements_from_script(self, script, recent_announcements, important_announcements):
        """Extract announcements from script tags"""
        try:
            # Look for JSON data containing announcements
            patterns = [
                r'announcements["\']?\s*:\s*(\[.*?\])',
                r'recent["\']?\s*:\s*(\[.*?\])',
                r'important["\']?\s*:\s*(\[.*?\])',
                r'data["\']?\s*:\s*\{.*?announcements["\']?\s*:\s*(\[.*?\])',
                r'items["\']?\s*:\s*(\[.*?\])',
                r'tabs["\']?\s*:\s*\{.*?recent["\']?\s*:\s*(\[.*?\])',
                r'tabs["\']?\s*:\s*\{.*?important["\']?\s*:\s*(\[.*?\])'
            ]
            
            for pattern in patterns:
                json_match = re.search(pattern, script.string, re.DOTALL)
                if json_match:
                    announcements_json = json.loads(json_match.group(1))
                    if isinstance(announcements_json, list):
                        for announcement in announcements_json:
                            if isinstance(announcement, dict):
                                title = announcement.get('title', announcement.get('label', announcement.get('name', '')))
                                url = announcement.get('url', announcement.get('href', announcement.get('link', '')))
                                date = announcement.get('date', announcement.get('time', announcement.get('created', '')))
                                
                                if title and any(keyword in title.lower() for keyword in [
                                    'announcement', 'disclosure', 'intimation', 'update', 'closure',
                                    'meeting', 'amalgamation', 'dissolution', 'regulation', 'sebi',
                                    'lodr', 'upsi', 'institutional', 'investor', 'summit', 'effective',
                                    'subsidiary', 'wholly-owned', 'participation', 'trading window',
                                    'press release', 'corporate action', 'board', 'dividend',
                                    'partnership', 'collaboration', 'transformation', 'deal',
                                    'migration', 'modernise', 'ai-powered', 'digital transformation'
                                ]):
                                    # Categorize based on content
                                    if any(keyword in title.lower() for keyword in [
                                        'press release', 'partnership', 'collaboration', 'transformation', 'deal',
                                        'migration', 'modernise', 'ai-powered', 'digital transformation',
                                        'vodafone', 'warehouse group', 'odisha', 'tryg', 'lloyds', 'scottish widows'
                                    ]):
                                        important_announcements.append({
                                            'label': title,
                                            'url': url,
                                            'date': date
                                        })
                                    else:
                                        recent_announcements.append({
                                            'label': title,
                                            'url': url,
                                            'date': date
                                        })
        except Exception:
            pass

    
    
    
    def _fetch_peers_from_api(self, symbol: str) -> List[Dict[str, str]]:
        """Try to fetch peer data from Screener.in API endpoints"""
        try:
            # Common API endpoints that Screener.in might use
            api_endpoints = [
                f"https://www.screener.in/api/company/{symbol}/peers/",
                f"https://www.screener.in/api/company/{symbol}/peer-comparison/",
                f"https://www.screener.in/api/company/{symbol}/competitors/",
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and 'peers' in data:
                            return data['peers']
                except Exception:
                    continue
            
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch peers from API: {e}")
            return []
    
    def _fetch_company_data_from_api(self, symbol: str) -> Dict[str, Any]:
        """Try to fetch company data from Screener.in API endpoints as fallback"""
        try:
            # Common API endpoints for company data
            api_endpoints = [
                f"https://www.screener.in/api/company/{symbol}/",
                f"https://www.screener.in/api/company/{symbol}/overview/",
                f"https://www.screener.in/api/company/{symbol}/ratios/",
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict):
                            return data
                except Exception:
                    continue
            
            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch company data from API: {e}")
            return {}
    
    def _fetch_pros_cons_from_api(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Try to fetch pros/cons data from Screener.in API endpoints"""
        try:
            # Extract symbol from the page URL or content
            symbol = None
            url_elem = soup.find('meta', {'property': 'og:url'})
            if url_elem and url_elem.get('content'):
                url_match = re.search(r'/company/([^/]+)/', url_elem.get('content'))
                if url_match:
                    symbol = url_match.group(1)
            
            if not symbol:
                return {'pros': [], 'cons': []}
            
            # Common API endpoints for pros/cons
            api_endpoints = [
                f"https://www.screener.in/api/company/{symbol}/analysis/",
                f"https://www.screener.in/api/company/{symbol}/pros-cons/",
                f"https://www.screener.in/api/company/{symbol}/insights/",
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict):
                            pros = data.get('pros', [])
                            cons = data.get('cons', [])
                            if pros or cons:
                                return {'pros': pros, 'cons': cons}
                except Exception:
                    continue
            
            return {'pros': [], 'cons': []}
        except Exception as e:
            logger.warning(f"Failed to fetch pros/cons from API: {e}")
            return {'pros': [], 'cons': []}
    
    def _aggregate_shareholding_yearly(self, shareholding_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Aggregate quarterly shareholding data into yearly averages
        
        Args:
            shareholding_data: List of shareholding records with quarterly columns
            
        Returns:
            List of shareholding records with yearly columns
        """
        if not shareholding_data:
            return []
        
        yearly_data = []
        
        for item in shareholding_data:
            yearly_item = {'': item.get('', 'Unknown')}
            
            # Get all date keys (exclude empty string)
            date_keys = [k for k in item.keys() if k != '']
            
            # Group by year
            years_data = {}
            for date_key in date_keys:
                # Extract year from date (e.g., "Jun 2025" -> "2025")
                year_match = re.search(r'(\d{4})', date_key)
                if year_match:
                    year = year_match.group(1)
                    if year not in years_data:
                        years_data[year] = []
                    
                    # Parse percentage value
                    value_str = item[date_key].replace('%', '').strip()
                    try:
                        value = float(value_str)
                        years_data[year].append(value)
                    except:
                        pass
            
            # Calculate yearly averages
            for year in sorted(years_data.keys()):
                values = years_data[year]
                if values:
                    avg_value = sum(values) / len(values)
                    yearly_item[year] = f"{avg_value:.2f}%"
            
            yearly_data.append(yearly_item)
        
        return yearly_data

    def _parse_table(self, table) -> List[Dict[str, str]]:
        """Parse HTML table into structured data with enhanced format handling"""
        if not table:
            return []
        
        rows = table.find_all('tr')
        if not rows:
            return []
        
        # Try to determine table structure
        first_row = rows[0]
        first_row_cells = first_row.find_all(['th', 'td'])
        
        # If first row has only one cell, it might be a single-column table
        if len(first_row_cells) == 1:
            return self._parse_single_column_table(table)
        
        # Standard multi-column table parsing
        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        data = []
        
        for row in rows[1:]:
            cols = row.find_all(['td', 'th'])
            if len(cols) > 0:
                row_data = {}
                for i, col in enumerate(cols):
                    header = headers[i] if i < len(headers) else f'Column_{i}'
                    value = col.get_text(strip=True)
                    row_data[header] = value
                data.append(row_data)
        
        return data
    
    def _parse_single_column_table(self, table) -> List[Dict[str, str]]:
        """Parse single-column tables (like financial statement headers)"""
        rows = table.find_all('tr')
        data = []
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                # Single cell contains the metric name
                metric_name = cells[0].get_text(strip=True)
                if metric_name:
                    data.append({'': metric_name})
        
        return data

    def _build_json_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive JSON structure for frontend
        
        Args:
            data: Fundamental data dictionary
            
        Returns:
            Formatted JSON data structure
        """
        json_data = {
            "metadata": {
                "symbol": data.get('symbol', ''),
                "url": data.get('url', ''),
                "fetch_timestamp": data.get('fetch_timestamp', ''),
                "extraction_version": "1.0",
                "source": "Screener.in"
            },
            "company_info": data.get('company_info', {}),
            "price_data": data.get('price_data', {}),
            "key_metrics": data.get('key_metrics', {}),
            "financial_statements": {
                "quarterly_results": data.get('quarterly_results', []),
                "profit_loss": data.get('profit_loss', []),
                "balance_sheet": data.get('balance_sheet', []),
                "cash_flow": data.get('cash_flow', [])
            },
            "ratios": data.get('ratios', []),
            "shareholding": data.get('shareholding', []),
            "peers": data.get('peers', []),
            "peers_comparison": data.get('peers_comparison', []),
            "about": data.get('about', {}),
            "pros_cons": data.get('pros_cons', {}),
            "documents": data.get('documents', {})
        }
        return json_data
    
    
    

    def get_fundamentals_with_json(self, symbol: str) -> Dict[str, Union[bool, str, Dict[str, Any]]]:
        """
        Get comprehensive fundamental data in JSON format
        
        Args:
            symbol: Stock symbol to fetch data for
            
        Returns:
            JSON response with success status and data
        """
        data = self.fetch_all_data(symbol)
        
        if data:
            # Build JSON response (no file storage)
            json_data = self._build_json_response(data)
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "source": "Screener.in",
                "symbol": symbol.upper(),
                "data": json_data
            }
        else:
            return {
                "success": False,
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol.upper(),
                "error": "Failed to fetch fundamental data. Please check the symbol and try again."
            }

    def search_stocks(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for stocks using Screener.in search functionality
        
        Args:
            query: Search query (symbol or company name)
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        try:
            # Clean the query
            query = query.strip().upper()
            if len(query) < 2:
                return {
                    "success": True,
                    "results": [],
                    "total": 0,
                    "query": query
                }
            
            # Try to search on Screener.in
            search_url = f"https://www.screener.in/api/company/search/?q={query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.screener.in/',
                'Origin': 'https://www.screener.in'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    search_data = response.json()
                    results = []
                    
                    # Process search results
                    if isinstance(search_data, list):
                        for item in search_data[:limit]:
                            if isinstance(item, dict):
                                results.append({
                                    "symbol": item.get("id", ""),
                                    "name": item.get("name", ""),
                                    "sector": item.get("sector", ""),
                                    "market_cap": item.get("market_cap", ""),
                                    "url": f"https://www.screener.in/company/{item.get('id', '')}/"
                                })
                    
                    return {
                        "success": True,
                        "results": results,
                        "total": len(results),
                        "query": query
                    }
                    
                except json.JSONDecodeError:
                    # If JSON parsing fails, return empty results
                    return {
                        "success": True,
                        "results": [],
                        "total": 0,
                        "query": query,
                        "message": "Search service temporarily unavailable"
                    }
            else:
                return {
                    "success": False,
                    "results": [],
                    "total": 0,
                    "query": query,
                    "error": f"Search service returned status {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "total": 0,
                "query": query,
                "error": str(e)
            }


# Main execution
if __name__ == "__main__":
    scraper = ScreenerFundamentalData()
    symbol = input("Enter Stock Symbol or Company Name (e.g., TCS, RELIANCE): ").strip()
    
    if not symbol:
        print("No symbol entered. Exiting.")
    else:
        # Get data with JSON export only
        result = scraper.get_fundamentals_with_json(symbol)
        
        if result["success"]:
            print(f"✅ Data fetched successfully for {symbol}")
            print(f"📄 Source: {result['source']}")
            print(f"⏰ Timestamp: {result['timestamp']}")
            print("\n📊 JSON Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error: {result['error']}")