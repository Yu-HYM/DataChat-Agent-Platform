import streamlit as st
import inspect
sig = inspect.signature(st.chat_input)
print("chat_input params:", list(sig.parameters.keys()))
