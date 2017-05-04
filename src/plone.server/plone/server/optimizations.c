#include <Python.h>
#include <frameobject.h>

static PyObject *RequestNotFound, *RequestHandler;

/* current_request frame obtainer */


static PyObject*
current_request()
{
	  PyFrameObject *f = PyThreadState_GET()->frame;
    int found = 0;
    PyObject *request = NULL;
    PyObject *self;
    while (found == 0 && f != NULL) {
      if (PyFrame_FastToLocalsWithError(f) < 0)
        return NULL;

			Py_INCREF(f->f_locals);

      if (PyDict_CheckExact(f->f_locals)) {
        self = PyDict_GetItem(f->f_locals, PyUnicode_FromString("self"));

        if (self != NULL) {

          if (PyObject_HasAttr(self, PyUnicode_FromString("request"))) {
            found = 1;
            request = PyObject_GetAttr(self, PyUnicode_FromString("request"));
          }
          if (PyObject_IsInstance(self, RequestHandler)) {
            found = 1;
            request = PyDict_GetItem(f->f_locals, PyUnicode_FromString("request"));
						Py_INCREF(request);
          }
        }
      }

			Py_DECCREF(f->f_locals);
      f = f->f_back;
    }


    if (f == NULL) {
        PyErr_SetString(RequestNotFound,
                        "Could not found the request");
        return NULL;
    }

    return (PyObject*)request;
}


static PyMethodDef OptimizationsMethods[] =
{
     {"get_current_request", current_request, METH_VARARGS, "Get the request"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC
PyInit_optimizations(void)
{

    PyObject* m;

	static struct PyModuleDef moduledef = {
         PyModuleDef_HEAD_INIT,
         "optimizations",
         "Optimizations plone server", -1, OptimizationsMethods, };
    PyObject* ob = PyModule_Create(&moduledef);

	if (ob == NULL)
	{
	    return NULL;
	}

    if ((m = PyImport_ImportModule("plone.server.exceptions")) == NULL)
    {
      return NULL;
    }

    RequestNotFound = PyObject_GetAttrString(m, "RequestNotFound");
    if (RequestNotFound == NULL)
    {
      return NULL;
    }
    Py_DECREF(m);

    if ((m = PyImport_ImportModule("aiohttp.web_server")) == NULL)
    {
      return NULL;
    }
    if ((RequestHandler = PyObject_GetAttrString(m, "RequestHandler")) == NULL)
    {
      return NULL;
    }
    Py_DECREF(m);

	return ob;
}
