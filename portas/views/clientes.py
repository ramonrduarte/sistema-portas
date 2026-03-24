from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect

from ..views_base import AtivoQuerysetMixin, BaseCRUDMixin, _get_perms, _sem_permissao
from ..models import Cliente, Pedido, PedidoStatusLog
from ..forms import ClienteForm

_PER_PAGE_OPCOES = [10, 20, 50]


class ClienteListView(LoginRequiredMixin, AtivoQuerysetMixin, ListView):
    model = Cliente
    template_name = "clientes/lista.html"
    context_object_name = "clientes"
    only_active = False
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["ver"]:
            return _sem_permissao("Você não tem permissão para visualizar clientes.")
        return super().dispatch(request, *args, **kwargs)

    def get_paginate_by(self, _queryset):
        try:
            per_page = int(self.request.GET.get("per_page", 20))
            return per_page if per_page in _PER_PAGE_OPCOES else 20
        except (ValueError, TypeError):
            return 20

    def get_queryset(self):
        _SORT_VALIDOS = {"codigo", "nome", "cpf_cnpj", "telefone", "email"}
        sort = self.request.GET.get("sort", "nome")
        if sort not in _SORT_VALIDOS:
            sort = "nome"
        direction = self.request.GET.get("dir", "asc")
        if direction not in ("asc", "desc"):
            direction = "asc"
        order = sort if direction == "asc" else f"-{sort}"
        qs = super().get_queryset().order_by(order)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nome__icontains=q) | Q(codigo__icontains=q) | Q(cpf_cnpj__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        _SORT_VALIDOS = {"codigo", "nome", "cpf_cnpj", "telefone", "email"}
        sort = self.request.GET.get("sort", "nome")
        direction = self.request.GET.get("dir", "asc")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["sort"] = sort if sort in _SORT_VALIDOS else "nome"
        ctx["dir"] = direction if direction in ("asc", "desc") else "asc"
        ctx["per_page"] = self.get_paginate_by(self.get_queryset())
        ctx["per_page_opcoes"] = _PER_PAGE_OPCOES
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request") == "true":
            return render(self.request, "clientes/_tabela.html", context)
        return super().render_to_response(context, **response_kwargs)


class ClienteCreateView(LoginRequiredMixin, BaseCRUDMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    success_url_name = "clientes_lista"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["editar"]:
            return _sem_permissao("Você não tem permissão para cadastrar clientes.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        return render(request, self.template_name, {"form": form, "object": None})

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            clientes = Cliente.objects.all().order_by("nome")
            resp = render(self.request, "clientes/_tabela.html", {"clientes": clientes})
            resp["HX-Trigger"] = "fecharModalCadastro"
            return resp
        return redirect(self.success_url_name)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "object": None})


class ClienteUpdateView(LoginRequiredMixin, BaseCRUDMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    success_url_name = "clientes_lista"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["editar"]:
            return _sem_permissao("Você não tem permissão para editar clientes.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            # Se veio da página de detalhe do cliente, redireciona de volta para ela
            current_url = self.request.headers.get("HX-Current-URL", "")
            detalhe_path = reverse("cliente_detalhe", args=[self.object.pk])
            if detalhe_path in current_url:
                resp = HttpResponse("")
                resp["HX-Redirect"] = detalhe_path
                return resp
            clientes = Cliente.objects.all().order_by("nome")
            resp = render(self.request, "clientes/_tabela.html", {"clientes": clientes})
            resp["HX-Trigger"] = "fecharModalCadastro"
            return resp
        return redirect(self.success_url_name)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "object": self.object})


class ClienteDeleteView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["excluir"]:
            return _sem_permissao("Você não tem permissão para excluir clientes.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        return render(request, "modais/excluir_produto.html", {
            "titulo": "Excluir cliente",
            "texto": f"Tem certeza que deseja excluir o cliente <strong>{cliente.nome}</strong>?",
            "post_url": "clientes_excluir",
            "obj_id": cliente.pk,
            "target_id": "#conteudoTabela",
        })

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.delete()
        if request.headers.get("HX-Request") == "true":
            clientes = Cliente.objects.all().order_by("nome")
            return render(request, "clientes/_tabela.html", {"clientes": clientes})
        return redirect("clientes_lista")


@login_required
def cliente_detalhe(request, pk):
    from django.db.models import Sum, Prefetch

    if not _get_perms(request.user)["clientes"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar clientes.")

    cliente = get_object_or_404(Cliente, pk=pk)

    pedidos = (
        Pedido.objects
        .filter(cliente=cliente)
        .prefetch_related(
            Prefetch(
                "status_logs",
                queryset=PedidoStatusLog.objects.order_by("alterado_em"),
            ),
            "itens",
        )
        .annotate(total=Sum("itens__valor_total"))
        .order_by("-id")
    )

    # Resumo por status e valor total geral
    resumo = {}
    total_valor = 0
    for p in pedidos:
        resumo[p.status] = resumo.get(p.status, 0) + 1
        total_valor += p.total or 0

    return render(request, "clientes/detalhe.html", {
        "cliente": cliente,
        "pedidos": pedidos,
        "resumo": resumo,
        "total_valor": total_valor,
        "status_labels": dict(Pedido.STATUS_CHOICES),
    })
