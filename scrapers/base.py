class BaseScraper:
    def __init__(self):
        self.name = "base"
    
    def scrape(self):
        raise NotImplementedError("Subclasses must implement scrape()")
