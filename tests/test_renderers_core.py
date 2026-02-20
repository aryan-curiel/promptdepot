import pytest
from promptdepot.renderers.core import PromptRenderer


class ConcreteRenderer(PromptRenderer[str, dict]):
    """Concrete implementation for testing the abstract base class."""

    def render(self, *, context: dict) -> str:
        return f"template={self.template}, config={self.config}, context={context}"


@pytest.fixture
def sample_template() -> str:
    return "Hello ${name}"


@pytest.fixture
def sample_config() -> dict:
    return {"strict_undefined": True, "trim_blocks": False}


def test_prompt_renderer_init__should_set_template_and_config(
    sample_template: str,
    sample_config: dict,
):
    renderer = ConcreteRenderer(template=sample_template, config=sample_config)

    assert renderer.template == sample_template
    assert renderer.config == sample_config


def test_prompt_renderer_init__should_accept_empty_config(
    sample_template: str,
):
    renderer = ConcreteRenderer(template=sample_template, config={})

    assert renderer.template == sample_template
    assert renderer.config == {}


def test_prompt_renderer_from_template__should_create_instance_with_correct_attributes(
    sample_template: str,
    sample_config: dict,
):
    renderer = ConcreteRenderer.from_template(
        template=sample_template, config=sample_config
    )

    assert isinstance(renderer, ConcreteRenderer)
    assert renderer.template == sample_template
    assert renderer.config == sample_config


def test_prompt_renderer_from_template__should_return_same_type_as_class():
    class CustomRenderer(PromptRenderer[str, dict]):
        def render(self, *, context: dict) -> str:
            return "custom"

    renderer = CustomRenderer.from_template(template="test", config={})

    assert type(renderer) is CustomRenderer
    assert type(renderer) is not ConcreteRenderer


def test_prompt_renderer_render__should_be_callable_on_concrete_implementation(
    sample_template: str,
    sample_config: dict,
):
    renderer = ConcreteRenderer(template=sample_template, config=sample_config)
    context = {"name": "World"}

    result = renderer.render(context=context)

    assert "template=Hello ${name}" in result
    assert "config={'strict_undefined': True, 'trim_blocks': False}" in result
    assert "context={'name': 'World'}" in result


def test_prompt_renderer__should_not_be_instantiable_without_render_implementation():
    class IncompleteRenderer(PromptRenderer[str, dict]):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteRenderer(template="test", config={})
