import gradio as gr
from utils.env_setup import setup_environment
from rag_respond_std_iface import rag_respond_std_iface


# Set up environment at startup
setup_environment()


# Create Gradio interface
iface = gr.Interface(
    fn=rag_respond_std_iface,
    inputs=gr.Textbox(lines=2, placeholder="Enter your question here..."),
    outputs="text",
    title="Jane Eyre RAG Chat",
    description="Ask questions about Jane Eyre (by Charlotte Brontë, 1847) and get answers based on the novel's content."
)


if __name__ == "__main__":
    iface.launch()

