from openai import OpenAI, DefaultHttpxClient
import streamlit as st
import os
import time

LOGO_SVG = "nutanix.svg"

if "iep_host_disabled" not in st.session_state:
    st.session_state["iep_host_disabled"] = False

def iep_host_disable():
    st.session_state["iep_host_disabled"] = True

if "endpoint_disabled" not in st.session_state:
    st.session_state["endpoint_disabled"] = False

def endpoint_disable():
    st.session_state["endpoint_disabled"] = True

if "apikey_disabled" not in st.session_state:
    st.session_state["apikey_disabled"] = False

def apikey_disable():
    st.session_state["apikey_disabled"] = True

if 'chat_disabled' not in st.session_state:
    st.session_state.chat_disabled = False

if 'set_values' not in st.session_state:
    st.session_state.set_values = False

if 'reset_values' not in st.session_state:
    st.session_state.reset_values = False

if 'chat_default' not in st.session_state:
    st.session_state.chat_default = "Ask me"

# App title
st.title("Demo Chatbot")

def clear_chat_history():
    """
    Clears the chat history by resetting the session state messages.
    """
    st.session_state.messages = []


with st.sidebar:
    if os.path.exists(LOGO_SVG):
        _, col2, _, _ = st.columns(4)
        with col2:
            st.image(LOGO_SVG, width=150)

    st.title("Nutanix Enterprise AI")
    st.markdown(
        "Nutanix Enterprise AI a simple way to securely deploy, scale, and run LLMs "
        " with NVIDIA NIM optimized inference microservices as well as open foundation "
        "models from Hugging Face. Read the [announcement]"
        "(https://www.nutanix.com/press-releases/2024/nutanix-extends-ai-platform-to-public-cloud)"
    )
    iep_host_name = st.sidebar.text_input(
            "Enter the Inference Endpoint URL", disabled=st.session_state.iep_host_disabled, on_change=iep_host_disable
    )

    st.subheader("Endpoint Configuration")
    endpoint_name = st.sidebar.text_input(
        "Enter the Endpoint name", disabled=st.session_state.endpoint_disabled, on_change=endpoint_disable
    )
    endpoint_api_key = st.sidebar.text_input(
        "Enter the Endpoint API key", disabled=st.session_state.apikey_disabled, on_change=apikey_disable, type="password"
    )

    if "iep_host_name" in st.session_state and st.session_state["iep_host_name"] != iep_host_name:
        clear_chat_history()

    if "endpoint_name" in st.session_state and st.session_state["endpoint_name"] != endpoint_name:
        clear_chat_history()

    if "endpoint_api_key" in st.session_state and st.session_state["endpoint_api_key"] != endpoint_api_key:
        clear_chat_history()

    st.session_state["iep_host_name"] = iep_host_name.strip()
    st.session_state["endpoint_name"] = endpoint_name.strip()
    st.session_state["endpoint_api_key"] = endpoint_api_key.strip()

    def set_values():
        st.session_state.set_values = True
        st.session_state.iep_host_disabled = True
        st.session_state.endpoint_disabled = True
        st.session_state.apikey_disabled = True

    def reset_values():
        st.session_state.reset_values = True
        st.session_state.iep_host_disabled = False
        st.session_state.endpoint_disabled = False
        st.session_state.apikey_disabled = False
        clear_chat_history()

    col1, _ ,col3 = st.columns(3)
    with col1:
        st.button('Save', on_click=set_values)
    with col3:
        st.button('Reset', on_click=reset_values, use_container_width=True)

#if st.session_state.set_values:
if not endpoint_name or not endpoint_api_key or not iep_host_name:
    st.session_state.chat_default="Endpoint URL, Name, and API key must be set"
    st.session_state.chat_disabled=True
else:
    st.session_state.chat_default="Ask me"
    st.session_state.chat_disabled=False

client = OpenAI(base_url=iep_host_name.removesuffix("/chat/completions"), api_key=endpoint_api_key, http_client=DefaultHttpxClient(verify=False))

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(st.session_state.chat_default, disabled=st.session_state.chat_disabled):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.chat_message("assistant"):
            start = time.perf_counter()
            stream = client.chat.completions.create(
                model=st.session_state["endpoint_name"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                max_tokens=1024,
                stream=True,
            )
            response = st.write_stream(stream)
        request_time = "{:.2f}".format(time.perf_counter() - start)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.markdown(f"Latency: {request_time} seconds")
        print(request_time)

    except Exception as e:
        print(e)
        st.error("Error. Did you set Inference Endpoint host name, Endpoint name and API key correctly?")
