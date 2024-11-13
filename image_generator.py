import typer
from openai import OpenAI
import requests
from PIL import Image
import io
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    BarColumn,
    TextColumn,
)
from pathlib import Path
import re
import time
from datetime import datetime
from anthropic import Anthropic
from enum import Enum

app = typer.Typer()
console = Console()


class ImageStyle(str, Enum):
    PHOTOREALISTIC = "photorealistic"
    CARTOON = "cartoon"
    ARTISTIC = "artistic"
    MINIMALIST = "minimalist"
    PIXEL_ART = "pixel_art"


class ImageSize(str, Enum):
    SQUARE = "square"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

    def get_dimensions(self) -> str:
        """Convert friendly name to DALL-E dimensions"""
        size_map = {
            "square": "1024x1024",
            "portrait": "1024x1792",
            "landscape": "1792x1024",
        }
        return size_map[self.value]


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )


class FlexibleImageGenerator:
    def __init__(
        self,
        anthropic_client: Anthropic,
        openai_client: OpenAI,
        temperature: float = 0.7,
        verbose: bool = False,
        filename: str | None = None,
        images_dir: Path | None = None,
    ):
        self.anthropic_client = anthropic_client
        self.openai_client = openai_client
        self.temperature = temperature
        self.verbose = verbose
        self.progress = create_progress()
        self.images_dir = images_dir

        # Set filename
        if filename:
            self.filename = self.sanitize_filename(filename)
        else:
            self.filename = datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Convert a string into a safe filename."""
        filename = re.sub(r"[^\w\s-]", "", filename)
        filename = re.sub(r"[-\s]+", "-", filename)
        filename = filename.lower().strip("-")
        return filename

    def generate_image_prompt(
        self,
        description: str,
        style: ImageStyle,
        additional_instructions: str | None = None,
    ) -> str:
        """Generate an optimized image prompt based on the description and style."""
        style_instructions = {
            ImageStyle.PHOTOREALISTIC: "Create a photorealistic image with high detail and natural lighting",
            ImageStyle.CARTOON: "Create a cartoon-style illustration with bold colors and clean lines",
            ImageStyle.ARTISTIC: "Create an artistic interpretation with creative expression and artistic flair",
            ImageStyle.MINIMALIST: "Create a minimalist design with clean, simple elements and plenty of negative space",
            ImageStyle.PIXEL_ART: "Create a pixel art style image with distinct pixels and limited color palette",
        }

        prompt = f"""Create an image generation prompt based on the following description:
Description: {description}

Style instructions: {style_instructions[style]}

Additional requirements:
1. Focus on visual elements and composition
2. Be specific about colors, lighting, and mood
3. Include details about perspective and framing
4. Maintain consistency with the chosen style
{f'5. {additional_instructions}' if additional_instructions else ''}

Write a clear, detailed prompt for DALL-E to create this image."""

        message = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=500,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text

    def generate_image(self, prompt: str, size: ImageSize = ImageSize.SQUARE) -> Path:
        """Generate an image using OpenAI's DALL-E 3 and save it."""
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size.get_dimensions(),
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            image_response = requests.get(image_url)
            image = Image.open(io.BytesIO(image_response.content))

            self.images_dir.mkdir(parents=True, exist_ok=True)
            image_path = self.images_dir / f"{self.filename}.png"
            image.save(image_path)

            return image_path

        except Exception as e:
            if self.verbose:
                console.print(
                    f"[yellow]Warning: Failed to generate image: {str(e)}[/yellow]"
                )
            raise

    async def generate(
        self,
        description: str,
        style: ImageStyle,
        size: ImageSize = ImageSize.SQUARE,
        additional_instructions: str | None = None,
    ) -> dict:
        """Generate an image with progress tracking."""
        start_time = time.time()

        with self.progress:
            progress_task = self.progress.add_task(
                "[cyan]Generating image...", total=100
            )

            # Generate optimized prompt (30% of progress)
            self.progress.update(
                progress_task, description="[cyan]Generating prompt..."
            )
            image_prompt = self.generate_image_prompt(
                description, style, additional_instructions
            )
            self.progress.update(progress_task, advance=30)

            # Generate image (60% of progress)
            self.progress.update(progress_task, description="[cyan]Creating image...")
            image_path = self.generate_image(image_prompt, size)
            self.progress.update(progress_task, advance=60)

            # Save image (final 10% of progress)
            self.progress.update(progress_task, description="[cyan]Saving image...")
            self.progress.update(progress_task, advance=10)

        generation_time = time.time() - start_time

        return {
            "image_path": image_path,
            "prompt": image_prompt,
            "generation_time": generation_time,
        }


async def run_generation(
    description: str,
    style: ImageStyle,
    images_dir: str,
    anthropic_api_key: str,
    openai_api_key: str,
    size: ImageSize = ImageSize.SQUARE,
    additional_instructions: str | None = None,
    temperature: float = 0.7,
    verbose: bool = False,
    filename: str | None = None,
):
    """Run image generation with progress tracking"""

    # Initialize clients
    anthropic_client = Anthropic(api_key=anthropic_api_key)
    openai_client = OpenAI(api_key=openai_api_key)

    # Use filename if provided, otherwise use sanitized description
    if not filename:
        filename = FlexibleImageGenerator.sanitize_filename(description[:30])

    # Convert path to Path object
    images_path = Path(images_dir)

    generator = FlexibleImageGenerator(
        anthropic_client=anthropic_client,
        openai_client=openai_client,
        temperature=temperature,
        verbose=verbose,
        filename=filename,
        images_dir=images_path,
    )

    results = await generator.generate(
        description, style, size, additional_instructions
    )

    console.print("\n[green]Generation Complete![/green]")
    console.print(f"Total processing time: {results['generation_time']:.2f} seconds")
    if verbose:
        console.print(f"Generated prompt: {results['prompt']}")
    console.print(f"\n[green]Image saved to: {results['image_path']}[/green]")


@app.command()
def create_image(
    description: str = typer.Argument(
        ..., help="Description of the image you want to generate"
    ),
    style: ImageStyle = typer.Option(
        ImageStyle.PHOTOREALISTIC,
        "--style",
        "-s",
        help="Style of the generated image",
    ),
    size: ImageSize = typer.Option(
        ImageSize.SQUARE,
        "--size",
        help="Size/aspect ratio of the generated image (square, portrait, or landscape)",
    ),
    additional_instructions: str = typer.Option(
        None,
        "--instructions",
        "-i",
        help="Additional instructions for image generation",
    ),
    filename: str | None = typer.Option(
        None,
        "--filename",
        "-f",
        help="Custom filename for the image (spaces will be replaced with hyphens)",
    ),
    images_dir: str = typer.Option(
        "./images",
        "--images-dir",
        "-d",
        help="Directory to save the generated images",
    ),
    temperature: float = typer.Option(
        0.7,
        "--temperature",
        "-t",
        help="Temperature for prompt generation",
    ),
    anthropic_api_key: str = typer.Option(
        None,
        "--anthropic-key",
        envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key",
    ),
    openai_api_key: str = typer.Option(
        None,
        "--openai-key",
        envvar="OPENAI_API_KEY",
        help="OpenAI API key",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output",
    ),
):
    """Generate an image based on your description using DALL-E 3."""
    try:
        # Validate API keys
        if not anthropic_api_key:
            console.print(
                "[red]Error: Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or use --anthropic-key[/red]"
            )
            raise typer.Exit(1)

        if not openai_api_key:
            console.print(
                "[red]Error: OpenAI API key is required. Set OPENAI_API_KEY environment variable or use --openai-key[/red]"
            )
            raise typer.Exit(1)

        import asyncio

        asyncio.run(
            run_generation(
                description=description,
                style=style,
                size=size,
                additional_instructions=additional_instructions,
                images_dir=images_dir,
                anthropic_api_key=anthropic_api_key,
                openai_api_key=openai_api_key,
                temperature=temperature,
                verbose=verbose,
                filename=filename,
            )
        )

    except Exception as e:
        console.print(f"[red]Error during generation: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
