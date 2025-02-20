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
@click.option('--is_favourite', is_flag=True, help='Generate favourite problems.')
def generate(is_favourite: bool):
    worker = LeetCodeCrawler()
    worker.login()
    
    if is_favourite:
        worker.fetch_favourite_problems()    
    else:    
        worker.fetch_accepted_problems()
    
    render_anki()


@cli.command()
@click.option('--slug', type=str, prompt='The slug of problem list')
@click.option('--size', type=int, prompt='Number of item wan to fetch')
def sync_favourite_list(slug: str, size: int):
    worker = LeetCodeCrawler()
    worker.login()
    
    worker.fetch_favourite_list(slug, 0, size)

if __name__ == '__main__':
    cli()