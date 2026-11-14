We can form the composite of two models `f` and `g` using the `>>` operator:
```
try: 
  p = f >> g
catch Exception:
  p = None
```
This process may not be well defined if the post-conditions ad outputs of `f` do
not align with the pre-conditions and inputs of `g`, but for now we will assume
that they can be composed.

```
y = p.run(x)
```
The interface can be parameterised by the data layer

```
y = p.run(x, data_store=Icechunk)
```

Q: do we always need to run `f` if there is already a result in the store for running `f` with
input `x`?

A: No, we cache results.  

Q: What if `f` is "free running" and has no inputs relevant to the top-level configuration?

A: A model is run not just with its inputs but also with its configuration. A configuration is
really an input but is seen as being separate to the input-output pathways which comes from
the dataflow within a (composite) model.

```
f = MyModel(config=Config)
```
initialises the model, and can provide the configuration.

