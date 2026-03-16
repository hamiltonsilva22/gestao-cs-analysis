import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_option_menu import option_menu
import os
import contextlib

st.set_page_config(page_title="Sistema de Gestão CS", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "carteira_cs.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
   c.execute('''CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    mrr REAL,
    faturamento REAL,
    media_pedidos REAL,
    responsavel TEXT,
    health TEXT,
    nivel TEXT,
    data_ultimo_touch TEXT,
    status_cliente TEXT
)''')
    c.execute('''CREATE TABLE IF NOT EXISTS acompanhamentos (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, data TEXT, tipo TEXT, avaliacao TEXT, observacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS atendimentos (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, data TEXT, tipo TEXT, 
                    modulo TEXT, descricao TEXT, status TEXT, solucao TEXT, data_solucao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS anotacoes (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, texto TEXT, data TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS addons (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, addon TEXT, valor REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS oportunidades (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, tipo TEXT, valor REAL, probabilidade INTEGER, status TEXT, previsao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tarefas (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, descricao TEXT, tipo TEXT, data TEXT, status TEXT, responsavel TEXT)''')
    conn.commit()
    conn.close()

init_db()

@contextlib.contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def run_query(query, params=()):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()

def load_data(query, params=()):
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)

def calcular_sla(nivel):
    if nivel in ['HIGH', 'HIGH++']: return 7
    elif nivel == 'MEDIUM': return 17
    elif nivel == 'LOW': return 25
    return 30

def calcular_dias_sem_touch(data_touch):
    if not data_touch:
        return 0
    try:
        ultima = datetime.strptime(data_touch, "%Y-%m-%d")
        return (datetime.now() - ultima).days
    except:
        return 0

def formata_data_br(df, colunas):
    for col in colunas:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y').fillna('-')
    return df

def parse_date(date_str):
    try: return datetime.strptime(date_str, '%Y-%m-%d').date()
    except: return datetime.now().date()

def str_data_br(date_str):
    try: return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except: return date_str

def get_idx(lista, valor):
    return lista.index(valor) if valor in lista else 0

MAPA_COLUNAS = {
    'nome': 'Cliente', 'mrr': 'MRR (R$)', 'status_cliente': 'Status Operacional',
    'responsavel': 'Key User', 'health': 'Saúde', 'nivel': 'Nível',
    'dias_sem_touch': 'Dias sem Touch', 'data': 'Data', 'tipo': 'Tipo',
    'avaliacao': 'Avaliação', 'observacao': 'Observação', 'texto': 'Texto/Anotação',
    'status': 'Status', 'addon': 'Addon', 'valor': 'Valor (R$)',
    'probabilidade': 'Probabilidade (%)', 'previsao': 'Previsão', 'descricao': 'Descrição',
    'faturamento': 'Faturamento (R$)', 'media_pedidos': 'Média de Pedidos',
    'modulo': 'Módulo', 'solucao': 'Solução', 'data_solucao': 'Data da Solução'
}

PLOTLY_CONFIG = {'displayModeBar': False} 
HOVER_STYLE = dict(bgcolor="#1E1E1E", font=dict(color="white", size=14, family="Arial"))

with st.sidebar:
    st.markdown("### Sistema de Gestão CS")
    menu = option_menu(
        menu_title=None, 
        options=[
            "Dashboard", "Clientes", "Cliente 360", "Cronograma SLA",
            "Atendimentos", "Acompanhamentos", "Anotações", 
            "Addons", "Oportunidades", "Tarefas", "Relatórios"
        ],
        icons=[
            'bar-chart-fill', 'people-fill', 'bullseye', 'calendar-check',
            'headset', 'chat-left-dots', 'journal-text', 'box-seam',
            'currency-dollar', 'check2-square', 'cloud-download'
        ],
        menu_icon="cast", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "white", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px", "--hover-color": "#2D2D2D"},
            "nav-link-selected": {"background-color": "#1E1E1E"},
        }
    )

df_clientes = load_data("SELECT * FROM clientes")
if not df_clientes.empty and "data_ultimo_touch" in df_clientes.columns:
    df_clientes["dias_sem_touch"] = df_clientes["data_ultimo_touch"].apply(calcular_dias_sem_touch)

lista_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
dict_clientes = dict(zip(df_clientes.nome, df_clientes.id)) if not df_clientes.empty else {}

if menu == "Dashboard":
    st.title("Painel Analítico")
    st.write("Visão consolidada de receita, risco e engajamento da carteira.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    if df_clientes.empty:
        st.info("Sistema sem dados. Por favor, cadastre clientes para gerar o painel analítico.")
    else:
        df_clientes['SLA (Dias)'] = df_clientes['nivel'].apply(calcular_sla)
        df_clientes['Status SLA'] = df_clientes.apply(lambda x: 'Atrasado' if x['dias_sem_touch'] > x['SLA (Dias)'] else 'Em dia', axis=1)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("MRR TOTAL", f"R$ {df_clientes['mrr'].sum():,.2f}")
        c2.metric("MRR EM RISCO", f"R$ {df_clientes[df_clientes['health'] == 'Risco']['mrr'].sum():,.2f}", delta_color="inverse")
        c3.metric("CLIENTES EM RISCO", len(df_clientes[df_clientes['health'] == 'Risco']))
        c4.metric("TOUCHS ATRASADOS", len(df_clientes[df_clientes['Status SLA'] == 'Atrasado']), delta_color="inverse")
        
        st.markdown("<br><hr><br>", unsafe_allow_html=True)

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            df_mrr_nivel = df_clientes.groupby('nivel')['mrr'].sum().reset_index()
            df_mrr_nivel['nivel'] = pd.Categorical(df_mrr_nivel['nivel'], categories=['HIGH++', 'HIGH', 'MEDIUM', 'LOW'], ordered=True)
            df_mrr_nivel = df_mrr_nivel.sort_values('nivel')
            fig_bar_mrr = px.bar(df_mrr_nivel, x='nivel', y='mrr', title='Receita (MRR) por Nível',
                                 color='nivel', color_discrete_map={'HIGH++':'#6610f2', 'HIGH':'#007bff', 'MEDIUM':'#17a2b8', 'LOW':'#6c757d'})
            fig_bar_mrr.update_traces(hovertemplate='<b>Nível:</b> %{x}<br><b>MRR:</b> R$ %{y:,.2f}<extra></extra>')
            fig_bar_mrr.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True), dragmode=False, hoverlabel=HOVER_STYLE)
            st.plotly_chart(fig_bar_mrr, use_container_width=True, config=PLOTLY_CONFIG)

        with col_graf2:
            df_sla_nivel = df_clientes.groupby(['nivel', 'Status SLA']).size().reset_index(name='Qtd')
            fig_bar_sla = px.bar(df_sla_nivel, y='nivel', x='Qtd', color='Status SLA', orientation='h',
                                 title='Aderência ao SLA por Nível', color_discrete_map={'Em dia': '#28a745', 'Atrasado': '#dc3545'})
            fig_bar_sla.update_traces(hovertemplate='<b>Nível:</b> %{y}<br><b>Status:</b> %{data.name}<br><b>Quantidade:</b> %{x} cliente(s)<extra></extra>')
            fig_bar_sla.update_layout(plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True), dragmode=False, hoverlabel=HOVER_STYLE)
            st.plotly_chart(fig_bar_sla, use_container_width=True, config=PLOTLY_CONFIG)

        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            fig_saude = px.pie(df_clientes, names='health', title='Saúde da Carteira', hole=0.4,
                               color='health', color_discrete_map={'Saudável': '#28a745', 'Atenção': '#ffc107', 'Risco': '#dc3545'})
            fig_saude.update_traces(hovertemplate='<b>Status:</b> %{label}<br><b>Quantidade:</b> %{value} cliente(s)<br><b>Proporção:</b> %{percent}<extra></extra>')
            fig_saude.update_layout(dragmode=False, hoverlabel=HOVER_STYLE)
            st.plotly_chart(fig_saude, use_container_width=True, config=PLOTLY_CONFIG)
            
        with col_graf4:
            fig_status = px.pie(df_clientes, values='mrr', names='status_cliente', title='MRR: Em Implantação vs Em Uso',
                                hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_status.update_traces(hovertemplate='<b>Status:</b> %{label}<br><b>MRR:</b> R$ %{value:,.2f}<br><b>Proporção:</b> %{percent}<extra></extra>')
            fig_status.update_layout(dragmode=False, hoverlabel=HOVER_STYLE)
            st.plotly_chart(fig_status, use_container_width=True, config=PLOTLY_CONFIG)

elif menu == "Clientes":
    st.title("Gestão de Clientes")
    
    tab_view, tab_add, tab_manage = st.tabs(["Visualizar Carteira", "Novo Cliente", "Gerenciar (Editar/Excluir)"])
    
    with tab_view:
        df_exibicao = df_clientes[['nome', 'mrr', 'status_cliente', 'responsavel', 'health', 'nivel', 'dias_sem_touch']].rename(columns=MAPA_COLUNAS)
        
        altura_dinamica = (len(df_exibicao) * 35) + 43 if not df_exibicao.empty else 200
        
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True, height=altura_dinamica)

    with tab_add:
        with st.form("form_novo_cliente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da Empresa *")
            responsavel = c2.text_input("Key User *") 
            c3, c4, c5 = st.columns(3)
            mrr, faturamento, media_pedidos = c3.number_input("MRR (R$)", min_value=0.0), c4.number_input("Faturamento (R$)", min_value=0.0), c5.number_input("Média de Pedidos", min_value=0)
            c6, c7, c8, c9 = st.columns(4)
            health, nivel = c6.selectbox("Saúde", ["Saudável", "Atenção", "Risco"]), c7.selectbox("Nível", ["HIGH++", "HIGH", "MEDIUM", "LOW"])
            status_cli, dias = c8.selectbox("Status Operacional", ["Em Implantação", "Em Uso", "Churn"]), c9.number_input("Dias sem contato", min_value=0, step=1)
            
            if st.form_submit_button("Salvar Registro"):
                if nome and responsavel:
                    run_query('''INSERT INTO clientes (nome, mrr, faturamento, media_pedidos, responsavel, health, nivel, dias_sem_touch,datetime.now().strftime("%Y-%m-%d"), status_cliente)
                                 VALUES (?,?,?,?,?,?,?,?,?)''', (nome, mrr, faturamento, media_pedidos, responsavel, health, nivel, dias, status_cli))
                    st.success("Cliente cadastrado com sucesso."); st.rerun()
                else: st.error("Os campos Nome e Key User são obrigatórios.")

    with tab_manage:
        if df_clientes.empty:
            st.info("Nenhum cliente cadastrado.")
        else:
            opcoes_cli = [f"[#{r['id']}] {r['nome']} - Key User: {r['responsavel']}" for _, r in df_clientes.iterrows()]
            dict_cli = {f"[#{r['id']}] {r['nome']} - Key User: {r['responsavel']}": r['id'] for _, r in df_clientes.iterrows()}
            
            cli_selecionado = st.selectbox("Selecione o cliente para gerenciar:", ["-- Selecione --"] + opcoes_cli)
            
            if cli_selecionado != "-- Selecione --":
                id_cli = dict_cli[cli_selecionado]
                df_alvo = load_data("SELECT * FROM clientes WHERE id=?", (id_cli,))
                rec = df_alvo.iloc[0]
                
                st.markdown("---")
                col_edit, col_del = st.columns([3, 1])
                with col_edit:
                    with st.form("form_edit_cli"):
                        st.subheader("Editar Cliente")
                        e_nome = st.text_input("Nome", value=rec['nome'])
                        e_resp = st.text_input("Key User", value=rec['responsavel'])
                        e_mrr = st.number_input("MRR", value=float(rec['mrr']))
                        e_fat = st.number_input("Faturamento", value=float(rec['faturamento']))
                        e_med = st.number_input("Média Pedidos", value=int(rec['media_pedidos']))
                        e_health = st.selectbox("Saúde", ["Saudável", "Atenção", "Risco"], index=get_idx(["Saudável", "Atenção", "Risco"], rec['health']))
                        e_nivel = st.selectbox("Nível", ["HIGH++", "HIGH", "MEDIUM", "LOW"], index=get_idx(["HIGH++", "HIGH", "MEDIUM", "LOW"], rec['nivel']))
                        e_status = st.selectbox("Status Operacional", ["Em Implantação", "Em Uso", "Churn"], index=get_idx(["Em Implantação", "Em Uso", "Churn"], rec['status_cliente']))
                        e_dias = st.number_input("Dias sem contato", value=int(rec['dias_sem_touch']), step=1)
                        
                        if st.form_submit_button("Salvar Alterações"):
                            run_query('''UPDATE clientes SET nome=?, mrr=?, faturamento=?, media_pedidos=?, responsavel=?, health=?, nivel=?, dias_sem_touch=?, status_cliente=? WHERE id=?''', 
                                      (e_nome, e_mrr, e_fat, e_med, e_resp, e_health, e_nivel, e_dias, e_status, id_cli))
                            st.success("Atualizado com sucesso!"); st.rerun()
                
                with col_del:
                    st.subheader("Ações Críticas")
                    st.warning("A exclusão é permanente.")
                    if st.button("Excluir Cliente", type="primary"):
                        run_query("DELETE FROM clientes WHERE id=?", (id_cli,))
                        st.success("Cliente excluído."); st.rerun()

elif menu == "Cliente 360":
    st.title("Visão Cliente 360")
    if not lista_clientes: 
        st.warning("Nenhum cliente disponível. Por favor, realize o cadastro na aba correspondente.")
    else:
        cli_sel = st.selectbox("Selecione o cliente:", lista_clientes)
        cli_id = dict_clientes[cli_sel]
        d_cli = df_clientes[df_clientes['id'] == cli_id].iloc[0]
        
        st.markdown(f"### {d_cli['nome']} - {d_cli['status_cliente']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("MRR", f"R$ {d_cli['mrr']:,.2f}")
        c2.metric("Saúde", d_cli['health'])
        c3.metric("Nível", d_cli['nivel'])
        
        sla = calcular_sla(d_cli['nivel'])
        atraso = d_cli['dias_sem_touch'] - sla
        c4.metric("Dias sem Touch", f"{d_cli['dias_sem_touch']} dias", f"SLA: {sla} dias ({'Atrasado' if atraso > 0 else 'Em dia'})", delta_color="inverse" if atraso > 0 else "normal")
        
        st.markdown("---")
        tab1, tab_atend, tab2, tab3, tab4, tab5 = st.tabs(["Timeline", "Atendimentos", "Oportunidades", "Tarefas", "Anotações", "Addons"])
        
        with tab1:
            df_acomp = formata_data_br(load_data("SELECT data, tipo, avaliacao, observacao FROM acompanhamentos WHERE cliente_id=?", (cli_id,)), ['data'])
            if not df_acomp.empty:
                for _, r in df_acomp.iterrows(): 
                    st.info(f"**{r['data']} | {r['tipo']} ({r['avaliacao']})**\n\n{r['observacao']}")
            else: 
                st.write("Nenhum registro de acompanhamento encontrado.")
            
        with tab_atend:
            st.dataframe(formata_data_br(load_data("SELECT data, tipo, modulo, descricao, status, solucao, data_solucao FROM atendimentos WHERE cliente_id=?", (cli_id,)), ['data', 'data_solucao']).rename(columns=MAPA_COLUNAS), use_container_width=True, hide_index=True)
        with tab2: st.dataframe(formata_data_br(load_data("SELECT tipo, valor, probabilidade, status, previsao FROM oportunidades WHERE cliente_id=?", (cli_id,)), ['previsao']).rename(columns=MAPA_COLUNAS), use_container_width=True, hide_index=True)
        with tab3: st.dataframe(formata_data_br(load_data("SELECT descricao, tipo, data, status, responsavel FROM tarefas WHERE cliente_id=?", (cli_id,)), ['data']).rename(columns=MAPA_COLUNAS), use_container_width=True, hide_index=True)
        with tab4: st.dataframe(formata_data_br(load_data("SELECT data, status, texto FROM anotacoes WHERE cliente_id=?", (cli_id,)), ['data']).rename(columns=MAPA_COLUNAS), use_container_width=True, hide_index=True)
        with tab5: st.dataframe(load_data("SELECT addon, valor, status FROM addons WHERE cliente_id=?", (cli_id,)).rename(columns=MAPA_COLUNAS), use_container_width=True, hide_index=True)

elif menu == "Cronograma SLA":
    st.title("Cronograma de Acompanhamentos")
    st.write("Acompanhamento de pendências de contato com base nas regras de SLA estabelecidas.")
    
    if not df_clientes.empty:
        df_cron = df_clientes[['nome', 'responsavel', 'nivel', 'status_cliente', 'dias_sem_touch']].copy()
        df_cron['Regra SLA (Dias)'] = df_cron['nivel'].apply(calcular_sla)
        df_cron['Dias Restantes'] = df_cron['Regra SLA (Dias)'] - df_cron['dias_sem_touch']
        df_cron['Status'] = df_cron['Dias Restantes'].apply(lambda x: 'Atrasado' if x < 0 else ('Vence em breve' if x <= 2 else 'Em dia'))
        df_cron = df_cron.sort_values(by='Dias Restantes', ascending=True)
        
        df_exibicao = df_cron[['Status', 'nome', 'responsavel', 'nivel', 'status_cliente', 'dias_sem_touch', 'Dias Restantes']].rename(columns=MAPA_COLUNAS)
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    else:
        st.info("Sistema sem dados. Por favor, cadastre clientes.")

elif menu in ["Atendimentos", "Acompanhamentos", "Anotações", "Addons", "Oportunidades", "Tarefas"]:
    modulo = menu
    tabelas = {"Atendimentos": "atendimentos", "Acompanhamentos": "acompanhamentos", "Anotações": "anotacoes", "Addons": "addons", "Oportunidades": "oportunidades", "Tarefas": "tarefas"}
    tabela_db = tabelas[modulo]
    
    st.title(f"Gestão de {modulo}")
    
    tab_view, tab_add, tab_manage = st.tabs(["Registros Atuais", "Adicionar Novo", "Gerenciar (Editar/Excluir)"])
    
    with tab_view:
        df_mod_view = load_data(f"SELECT c.nome as Cliente, t.* FROM {tabela_db} t JOIN clientes c ON t.cliente_id = c.id ORDER BY t.id DESC").drop(columns=['cliente_id', 'id'])
        if not df_mod_view.empty:
            colunas_data = ['data', 'previsao', 'data_solucao']
            st.dataframe(formata_data_br(df_mod_view, [c for c in colunas_data if c in df_mod_view.columns]).rename(columns=MAPA_COLUNAS), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro encontrado.")

    with tab_add:
        if not lista_clientes: st.warning("Cadastre um cliente antes.")
        else:
            with st.form(f"form_add_{modulo}", clear_on_submit=True):
                cli_id = dict_clientes[st.selectbox("Cliente", lista_clientes)]
                hoje = datetime.now().strftime('%Y-%m-%d')
                
                if modulo == "Atendimentos":
                    d1, d2 = st.columns(2)
                    data = d1.date_input("Data", format="DD/MM/YYYY")
                    tipo = d2.selectbox("Tipo", ["Atendimento", "Reunião"])
                    d3, d4 = st.columns(2)
                    mod, desc = d3.text_input("Módulo (Opcional)"), d4.text_input("Descrição")
                    d5, d6 = st.columns(2)
                    status, solucao = d5.selectbox("Status", ["Resolvido", "Pendente", "Em Andamento"]), d6.text_input("Solução")
                    data_solucao = st.date_input("Data da Solução", format="DD/MM/YYYY")
                    if st.form_submit_button("Salvar Registro"):
                        run_query("INSERT INTO atendimentos (cliente_id, data, tipo, modulo, descricao, status, solucao, data_solucao) VALUES (?,?,?,?,?,?,?,?)", (cli_id, data, tipo, mod, desc, status, solucao, data_solucao))
                        run_query(
    "UPDATE clientes SET data_ultimo_touch = ? WHERE id = ?",
    (datetime.now().strftime("%Y-%m-%d"), cli_id)
)
                        st.success("Salvo com sucesso!"); st.rerun()

                elif modulo == "Acompanhamentos":
                    d1, d2, d3 = st.columns(3)
                    data = d1.date_input("Data", format="DD/MM/YYYY")
                    tipo = d2.selectbox("Tipo", ["Reunião QBR", "Suporte", "Follow-up", "Onboarding", "Renovação"])
                    aval = d3.selectbox("Avaliação", ["Positiva", "Neutra", "Negativa"])
                    obs = st.text_area("Observação")
                    if st.form_submit_button("Salvar Registro"):
                        run_query("INSERT INTO acompanhamentos (cliente_id, data, tipo, avaliacao, observacao) VALUES (?,?,?,?,?)", (cli_id, data, tipo, aval, obs))
                        run_query("UPDATE clientes SET dias_sem_touch = 0 WHERE id = ?", (cli_id,))
                        st.success("Salvo com sucesso!"); st.rerun()

                elif modulo == "Anotações":
                    texto, status = st.text_area("Anotação"), st.selectbox("Status", ["Ativa", "Resolvida"])
                    if st.form_submit_button("Salvar Registro"):
                        run_query("INSERT INTO anotacoes (cliente_id, texto, data, status) VALUES (?,?,?,?)", (cli_id, texto, hoje, status)); st.success("Salvo!"); st.rerun()

                elif modulo == "Addons":
                    addon, valor, status = st.text_input("Módulo"), st.number_input("Valor (R$)", min_value=0.0), st.selectbox("Status", ["Ativo", "Cancelado"])
                    if st.form_submit_button("Salvar Registro"):
                        run_query("INSERT INTO addons (cliente_id, addon, valor, status) VALUES (?,?,?,?)", (cli_id, addon, valor, status)); st.success("Salvo!"); st.rerun()

                elif modulo == "Oportunidades":
                    tipo, valor, prob = st.selectbox("Tipo", ["Upsell", "Cross-sell", "Addon"]), st.number_input("Valor Estimado", min_value=0.0), st.slider("Probabilidade", 0, 100, 50)
                    status, previsao = st.selectbox("Status", ["Aberta", "Ganha", "Perdida"]), st.date_input("Previsão", format="DD/MM/YYYY")
                    if st.form_submit_button("Salvar Registro"):
                        run_query("INSERT INTO oportunidades (cliente_id, tipo, valor, probabilidade, status, previsao) VALUES (?,?,?,?,?,?)", (cli_id, tipo, valor, prob, status, previsao)); st.success("Salvo!"); st.rerun()

                elif modulo == "Tarefas":
                    desc, tipo, data = st.text_input("Descrição"), st.selectbox("Tipo", ["Follow-up", "Reunião", "Ação Interna", "Risco"]), st.date_input("Prazo", format="DD/MM/YYYY")
                    status, resp = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluída"]), st.text_input("Responsável")
                    if st.form_submit_button("Salvar Registro"):
                        run_query("INSERT INTO tarefas (cliente_id, descricao, tipo, data, status, responsavel) VALUES (?,?,?,?,?,?)", (cli_id, desc, tipo, data, status, resp)); st.success("Salvo!"); st.rerun()

    with tab_manage:
        df_all_mod = load_data(f"SELECT c.nome as Cliente, t.* FROM {tabela_db} t JOIN clientes c ON t.cliente_id = c.id ORDER BY t.id DESC")
        
        if df_all_mod.empty:
            st.info("Nenhum registro para gerenciar.")
        else:
            opcoes_mod = []
            dict_mod = {}
            for _, r in df_all_mod.iterrows():
                data_br = str_data_br(r.get('data', ''))
                prev_br = str_data_br(r.get('previsao', ''))
                
                if modulo == "Atendimentos": lbl = f"[#{r['id']}] {r['Cliente']} - {data_br} ({r['tipo']})"
                elif modulo == "Acompanhamentos": lbl = f"[#{r['id']}] {r['Cliente']} - {data_br} ({r['tipo']})"
                elif modulo == "Anotações": lbl = f"[#{r['id']}] {r['Cliente']} - {data_br}"
                elif modulo == "Addons": lbl = f"[#{r['id']}] {r['Cliente']} - Módulo: {r['addon']}"
                elif modulo == "Oportunidades": lbl = f"[#{r['id']}] {r['Cliente']} - {r['tipo']} (Previsão: {prev_br})"
                elif modulo == "Tarefas": lbl = f"[#{r['id']}] {r['Cliente']} - {r['descricao'][:25]}... (Prazo: {data_br})"
                
                opcoes_mod.append(lbl)
                dict_mod[lbl] = r['id']
                
            reg_selecionado = st.selectbox("Selecione o registro para editar ou excluir:", ["-- Selecione --"] + opcoes_mod)
            
            if reg_selecionado != "-- Selecione --":
                id_alvo = dict_mod[reg_selecionado]
                rec = df_all_mod[df_all_mod['id'] == id_alvo].iloc[0]
                
                st.markdown("---")
                col_e, col_d = st.columns([3, 1])
                with col_d:
                    st.subheader("Ações Críticas")
                    st.warning("A exclusão é permanente.")
                    if st.button("Excluir Registro", type="primary"):
                        run_query(f"DELETE FROM {tabela_db} WHERE id=?", (id_alvo,)); st.success("Excluído!"); st.rerun()
                        
                with col_e:
                    st.subheader("Editar Registro")
                    with st.form(f"form_edit_{modulo}"):
                        if modulo == "Atendimentos":
                            e_data, e_tipo = st.date_input("Data", value=parse_date(rec['data']), format="DD/MM/YYYY"), st.selectbox("Tipo", ["Atendimento", "Reunião"], index=get_idx(["Atendimento", "Reunião"], rec['tipo']))
                            e_mod, e_desc = st.text_input("Módulo", value=rec['modulo']), st.text_input("Descrição", value=rec['descricao'])
                            e_status, e_sol = st.selectbox("Status", ["Resolvido", "Pendente", "Em Andamento"], index=get_idx(["Resolvido", "Pendente", "Em Andamento"], rec['status'])), st.text_input("Solução", value=rec['solucao'])
                            e_datasol = st.date_input("Data da Solução", value=parse_date(rec['data_solucao']), format="DD/MM/YYYY")
                            if st.form_submit_button("Salvar Edição"):
                                run_query("UPDATE atendimentos SET data=?, tipo=?, modulo=?, descricao=?, status=?, solucao=?, data_solucao=? WHERE id=?", (e_data, e_tipo, e_mod, e_desc, e_status, e_sol, e_datasol, id_alvo)); st.rerun()
                                
                        elif modulo == "Acompanhamentos":
                            e_data, e_tipo = st.date_input("Data", value=parse_date(rec['data']), format="DD/MM/YYYY"), st.selectbox("Tipo", ["Reunião QBR", "Suporte", "Follow-up", "Onboarding", "Renovação"], index=get_idx(["Reunião QBR", "Suporte", "Follow-up", "Onboarding", "Renovação"], rec['tipo']))
                            e_aval, e_obs = st.selectbox("Avaliação", ["Positiva", "Neutra", "Negativa"], index=get_idx(["Positiva", "Neutra", "Negativa"], rec['avaliacao'])), st.text_area("Observação", value=rec['observacao'])
                            if st.form_submit_button("Salvar Edição"):
                                run_query("UPDATE acompanhamentos SET data=?, tipo=?, avaliacao=?, observacao=? WHERE id=?", (e_data, e_tipo, e_aval, e_obs, id_alvo)); st.rerun()
                                
                        elif modulo == "Anotações":
                            e_texto, e_status = st.text_area("Anotação", value=rec['texto']), st.selectbox("Status", ["Ativa", "Resolvida"], index=get_idx(["Ativa", "Resolvida"], rec['status']))
                            if st.form_submit_button("Salvar Edição"):
                                run_query("UPDATE anotacoes SET texto=?, status=? WHERE id=?", (e_texto, e_status, id_alvo)); st.rerun()
                                
                        elif modulo == "Addons":
                            e_addon, e_valor, e_status = st.text_input("Módulo", value=rec['addon']), st.number_input("Valor", value=float(rec['valor'])), st.selectbox("Status", ["Ativo", "Cancelado"], index=get_idx(["Ativo", "Cancelado"], rec['status']))
                            if st.form_submit_button("Salvar Edição"):
                                run_query("UPDATE addons SET addon=?, valor=?, status=? WHERE id=?", (e_addon, e_valor, e_status, id_alvo)); st.rerun()
                                
                        elif modulo == "Oportunidades":
                            e_tipo, e_valor, e_prob = st.selectbox("Tipo", ["Upsell", "Cross-sell", "Addon"], index=get_idx(["Upsell", "Cross-sell", "Addon"], rec['tipo'])), st.number_input("Valor", value=float(rec['valor'])), st.slider("Probabilidade", 0, 100, int(rec['probabilidade']))
                            e_status, e_prev = st.selectbox("Status", ["Aberta", "Ganha", "Perdida"], index=get_idx(["Aberta", "Ganha", "Perdida"], rec['status'])), st.date_input("Previsão", value=parse_date(rec['previsao']), format="DD/MM/YYYY")
                            if st.form_submit_button("Salvar Edição"):
                                run_query("UPDATE oportunidades SET tipo=?, valor=?, probabilidade=?, status=?, previsao=? WHERE id=?", (e_tipo, e_valor, e_prob, e_status, e_prev, id_alvo)); st.rerun()
                                
                        elif modulo == "Tarefas":
                            e_desc, e_tipo, e_data = st.text_input("Descrição", value=rec['descricao']), st.selectbox("Tipo", ["Follow-up", "Reunião", "Ação Interna", "Risco"], index=get_idx(["Follow-up", "Reunião", "Ação Interna", "Risco"], rec['tipo'])), st.date_input("Prazo", value=parse_date(rec['data']), format="DD/MM/YYYY")
                            e_status, e_resp = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluída"], index=get_idx(["Pendente", "Em Andamento", "Concluída"], rec['status'])), st.text_input("Responsável", value=rec['responsavel'])
                            if st.form_submit_button("Salvar Edição"):
                                run_query("UPDATE tarefas SET descricao=?, tipo=?, data=?, status=?, responsavel=? WHERE id=?", (e_desc, e_tipo, e_data, e_status, e_resp, id_alvo)); st.rerun()

elif menu == "Relatórios":
    st.title("Relatórios e Exportação")
    st.write("Exporte as bases de dados nos formatos padrão.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Base de Clientes")
        if not df_clientes.empty:
            csv_cli = df_clientes.drop(columns=['id']).to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Clientes (CSV)", csv_cli, 'clientes.csv', 'text/csv', type="primary", use_container_width=True)

    with col2:
        st.subheader("Atendimentos")
        df_atend_rel = load_data("SELECT c.nome as Cliente, a.data, a.tipo, a.modulo, a.descricao, a.status, a.solucao, a.data_solucao FROM atendimentos a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.data DESC")
        if not df_atend_rel.empty:
            csv_atend = formata_data_br(df_atend_rel, ['data', 'data_solucao']).to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Atendimentos", csv_atend, 'atendimentos.csv', 'text/csv', type="primary", use_container_width=True)

    with col3:
        st.subheader("Acompanhamentos")
        df_acomp_rel = load_data("SELECT c.nome as Cliente, a.data, a.tipo, a.avaliacao, a.observacao FROM acompanhamentos a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.data DESC")
        if not df_acomp_rel.empty:
            csv_acomp = formata_data_br(df_acomp_rel, ['data']).to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Acompanhamentos", csv_acomp, 'acompanhamentos.csv', 'text/csv', type="primary", use_container_width=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.subheader("Oportunidades")
        df_opp_rel = load_data("SELECT c.nome as Cliente, o.tipo, o.valor, o.probabilidade, o.status, o.previsao FROM oportunidades o JOIN clientes c ON o.cliente_id = c.id ORDER BY o.id DESC")
        if not df_opp_rel.empty:
            csv_opp = formata_data_br(df_opp_rel, ['previsao']).to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Oportunidades", csv_opp, 'oportunidades.csv', 'text/csv', type="primary", use_container_width=True)

    with col5:
        st.subheader("Tarefas")
        df_tar_rel = load_data("SELECT c.nome as Cliente, t.descricao, t.tipo, t.data, t.status, t.responsavel FROM tarefas t JOIN clientes c ON t.cliente_id = c.id ORDER BY t.data DESC")
        if not df_tar_rel.empty:
            csv_tar = formata_data_br(df_tar_rel, ['data']).to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Tarefas", csv_tar, 'tarefas.csv', 'text/csv', type="primary", use_container_width=True)

    with col6:
        st.subheader("Anotações e Addons")
        df_nota_rel = load_data("SELECT c.nome as Cliente, a.texto, a.data, a.status FROM anotacoes a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.id DESC")
        if not df_nota_rel.empty:
            csv_nota = formata_data_br(df_nota_rel, ['data']).to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Anotações", csv_nota, 'anotacoes.csv', 'text/csv', type="primary", use_container_width=True)
        
        df_add_rel = load_data("SELECT c.nome as Cliente, a.addon, a.valor, a.status FROM addons a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.id DESC")
        if not df_add_rel.empty:
            csv_add = df_add_rel.to_csv(index=False).encode('utf-8')
            st.download_button("Exportar Addons", csv_add, 'addons.csv', 'text/csv', type="primary", use_container_width=True)
