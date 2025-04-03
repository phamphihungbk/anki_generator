import csv

from database import LeetCodeTrack

file_name = 'leetcode-tracker.csv'

class CSVProcessor:

    def sync_leetcode_track(self):
        with open(file_name, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                LeetCodeTrack.replace(
                    title=row['Problem'],
                    status='TO_DO'
                ).execute()
                