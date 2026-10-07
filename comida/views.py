from django.shortcuts import render, redirect
from django.db import connection


# PÁGINA PRINCIPAL

def inicio(request):
    return render(request, 'comida/inicio.html')


# LISTAR COMIDAS

def lista_comidas(request):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id, nombre, descripcion, precio, categoria, disponible
            FROM comida_comida
            ORDER BY id DESC
        """)

        filas = cursor.fetchall()

    comidas = []

    for fila in filas:

        comidas.append({
            'id': fila[0],
            'nombre': fila[1],
            'descripcion': fila[2],
            'precio': fila[3],
            'categoria': fila[4],
            'disponible': fila[5],
        })

    return render(
        request,
        'comida/lista.html',
        {'comidas': comidas}
    )


# CREAR COMIDA

def crear_comida(request):

    if request.method == 'POST':

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        categoria = request.POST.get('categoria')

        with connection.cursor() as cursor:

            cursor.execute("""
                INSERT INTO comida_comida
                (nombre, descripcion, precio, categoria, disponible)
                VALUES (%s, %s, %s, %s, %s)
            """, [
                nombre,
                descripcion,
                precio,
                categoria,
                True
            ])

        return redirect('lista_comidas')

    return render(request, 'comida/crear.html')



# EDITAR COMIDA


def editar_comida(request, id):

    if request.method == 'POST':

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        categoria = request.POST.get('categoria')
        disponible = request.POST.get('disponible') == 'on'

        with connection.cursor() as cursor:

            cursor.execute("""
                UPDATE comida_comida
                SET nombre = %s,
                    descripcion = %s,
                    precio = %s,
                    categoria = %s,
                    disponible = %s
                WHERE id = %s
            """, [
                nombre,
                descripcion,
                precio,
                categoria,
                disponible,
                id
            ])

        return redirect('lista_comidas')

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id, nombre, descripcion, precio, categoria, disponible
            FROM comida_comida
            WHERE id = %s
        """, [id])

        fila = cursor.fetchone()

    if fila is None:
        return redirect('lista_comidas')

    comida = {
        'id': fila[0],
        'nombre': fila[1],
        'descripcion': fila[2],
        'precio': fila[3],
        'categoria': fila[4],
        'disponible': fila[5],
    }

    return render(
        request,
        'comida/editar.html',
        {'comida': comida}
    )


# LIMINAR COMIDA

def eliminar_comida(request, id):

    if request.method == 'POST':

        with connection.cursor() as cursor:

            cursor.execute("""
                DELETE FROM comida_comida
                WHERE id = %s
            """, [id])

        return redirect('lista_comidas')

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id, nombre
            FROM comida_comida
            WHERE id = %s
        """, [id])

        fila = cursor.fetchone()

    if fila is None:
        return redirect('lista_comidas')

    comida = {
        'id': fila[0],
        'nombre': fila[1],
    }

    return render(
        request,
        'comida/eliminar.html',
        {'comida': comida}
    )