from csv_processor import CSVProcessor
from database import create_tables
from crawler import LeetCodeCrawler
from renderer import render_anki
import click

create_tables()


@click.group()
def cli():
    """Main CLI"""
    pass    


@cli.command()
@click.option('--contain_solution', is_flag=False, help='Does you need to fecth solution or submission.')
def fetch_question_detail(contain_solution: bool):
    worker = LeetCodeCrawler()
    worker.login()
    worker.fetch_favourite_problems(contain_solution)    
    
    render_anki()


@cli.command()
@click.option('--slug', type=str, prompt='The slug of problem list.')
@click.option('--size', type=int, prompt='Number of item want to fetch.')
def fetch_favourite_questions(slug: str, size: int):
    worker = LeetCodeCrawler()
    worker.login()
    
    worker.fetch_favourite_questions(slug, 0, size)
    

@cli.command()
@click.option('--slug', type=click.Choice(['amazon-all', 'google-all', 'facebook-all', 'microsoft-all']), prompt='The company slug')
@click.option('--size', type=int, prompt='Number of item want to fetch.')
def fetch_top_questions(slug: str, size: int):
    worker = LeetCodeCrawler()
    worker.login()
    
    worker.fetch_top_questions_by_company(slug, 0, size)
    

@cli.command()
def sync_leetcode_track():
    worker = CSVProcessor()
    worker.sync_leetcode_track()    


@cli.command()
def generate_deck():
    render_anki()


if __name__ == '__main__':
    cli()